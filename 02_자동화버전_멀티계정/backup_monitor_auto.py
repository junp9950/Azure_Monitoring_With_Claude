import json
import logging
from datetime import datetime, timezone, timedelta
from azure.identity import InteractiveBrowserCredential
from azure.mgmt.recoveryservices import RecoveryServicesClient
from azure.mgmt.recoveryservicesbackup import RecoveryServicesBackupClient
from azure.core.exceptions import AzureError

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'backup_monitor_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

def load_accounts_config():
    """계정 설정 파일 로드"""
    try:
        with open('../계정설정_공통.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error("계정설정_공통.json 파일을 찾을 수 없습니다.")
        return None
    except json.JSONDecodeError:
        logging.error("설정 파일 형식이 올바르지 않습니다.")
        return None

def get_backup_jobs(account_info):
    """특정 계정의 백업 작업 조회"""
    try:
        print(f"\n=== {account_info['name']} 계정 처리 중... ===")
        
        # 인증
        credential = InteractiveBrowserCredential(tenant_id=account_info['tenant_id'])
        
        # Recovery Services Client 생성
        recovery_client = RecoveryServicesClient(credential, account_info['subscription_id'])
        
        # Vault 목록 조회
        vaults = list(recovery_client.vaults.list_by_subscription_id())
        
        if not vaults:
            logging.warning(f"{account_info['name']}: Recovery Services Vault가 없습니다.")
            return []
        
        # Backup Client 생성
        backup_client = RecoveryServicesBackupClient(credential, account_info['subscription_id'])
        
        all_jobs = []
        KST = timezone(timedelta(hours=9))
        
        for vault in vaults:
            vault_name = vault.name
            resource_group = vault.id.split('/')[4]
            
            print(f"  - Vault: {vault_name}")
            
            try:
                # 백업 작업 조회
                jobs = backup_client.backup_jobs.list(vault_name, resource_group)
                
                for job in jobs:
                    start_utc = job.properties.start_time
                    start_kst = start_utc.astimezone(KST) if start_utc else None
                    
                    job_info = {
                        'account_name': account_info['name'],
                        'vault_name': vault_name,
                        'job_id': job.name,
                        'status': job.properties.status,
                        'start_time': start_kst.strftime('%Y-%m-%d %H:%M:%S') if start_kst else 'N/A',
                        'start_time_raw': start_kst
                    }
                    all_jobs.append(job_info)
                    
            except Exception as e:
                logging.error(f"Vault {vault_name} 백업 작업 조회 실패: {str(e)}")
                continue
        
        logging.info(f"{account_info['name']}: {len(all_jobs)}개 백업 작업 조회 완료")
        return all_jobs
        
    except AzureError as e:
        logging.error(f"{account_info['name']} Azure 오류: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"{account_info['name']} 처리 중 오류: {str(e)}")
        return []

def print_summary(all_jobs):
    """결과 요약 출력"""
    print("\n" + "="*80)
    print("                       백업 모니터링 요약 결과")
    print("="*80)
    
    if not all_jobs:
        print("조회된 백업 작업이 없습니다.")
        return
    
    # 계정별 통계
    account_stats = {}
    failed_jobs = []
    
    for job in all_jobs:
        account = job['account_name']
        if account not in account_stats:
            account_stats[account] = {'total': 0, 'completed': 0, 'failed': 0}
        
        account_stats[account]['total'] += 1
        
        if job['status'] == 'Completed':
            account_stats[account]['completed'] += 1
        elif job['status'] in ['Failed', 'Cancelled']:
            account_stats[account]['failed'] += 1
            failed_jobs.append(job)
    
    # 계정별 통계 출력
    for account, stats in account_stats.items():
        print(f"\n[{account}]")
        print(f"  총 백업 작업: {stats['total']}개")
        print(f"  성공: {stats['completed']}개")
        print(f"  실패: {stats['failed']}개")
    
    # 실패한 작업 상세 정보
    if failed_jobs:
        print(f"\n🚨 실패한 백업 작업 ({len(failed_jobs)}개):")
        for job in failed_jobs:
            print(f"  - {job['account_name']} | {job['vault_name']} | {job['status']} | {job['start_time']}")
    
    # 최근 백업 작업
    if all_jobs:
        today = datetime.now().date()
        today_jobs = [job for job in all_jobs if job['start_time_raw'] and job['start_time_raw'].date() == today]
        
        print(f"\n📅 오늘 실행된 백업 작업 ({len(today_jobs)}개):")
        for job in today_jobs:
            status_icon = "✅" if job['status'] == 'Completed' else "❌"
            print(f"  {status_icon} {job['account_name']} | {job['vault_name']} | {job['start_time']}")

def main():
    """메인 실행 함수"""
    print("Azure 백업 모니터링 자동화 시스템")
    print("="*50)
    
    # 설정 파일 로드
    config = load_accounts_config()
    if not config:
        print("설정 파일 로드 실패")
        return
    
    accounts = config.get('accounts', [])
    if not accounts:
        print("설정된 계정이 없습니다.")
        return
    
    print(f"총 {len(accounts)}개 계정 처리 예정")
    
    # 모든 계정 처리
    all_jobs = []
    for account in accounts:
        jobs = get_backup_jobs(account)
        all_jobs.extend(jobs)
    
    # 결과 요약
    print_summary(all_jobs)
    
    print(f"\n실행 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"로그 파일: backup_monitor_{datetime.now().strftime('%Y%m%d')}.log")

if __name__ == "__main__":
    main()