import json
import logging

# YAML 모듈 자동 설치
try:
    import yaml
except ImportError:
    import subprocess
    import sys
    print("PyYAML 패키지를 설치 중입니다...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyYAML>=6.0"])
    import yaml
    print("PyYAML 설치 완료!")
from datetime import datetime, timezone, timedelta
from azure.identity import ClientSecretCredential
from azure.mgmt.recoveryservices import RecoveryServicesClient
from azure.mgmt.recoveryservicesbackup import RecoveryServicesBackupClient
from azure.core.exceptions import AzureError

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'backup_monitor_sp_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

def load_accounts_config():
    """Service Principal 계정 설정 파일 로드"""
    try:
        # YAML 파일 먼저 시도
        with open('../계정설정_ServicePrincipal.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        try:
            # 기존 JSON 파일 백업으로 시도
            with open('../계정설정_서비스프린시팔.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error("계정설정 파일을 찾을 수 없습니다.")
            print("❌ 설정 파일 없음: 계정설정_ServicePrincipal.yaml 또는 계정설정_서비스프린시팔.json 파일을 생성하고 Service Principal 정보를 입력하세요.")
            return None
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        logging.error(f"설정 파일 형식이 올바르지 않습니다: {e}")
        print(f"❌ 설정 파일 오류: 형식을 확인하세요. {e}")
        return None

def validate_account_config(account_info):
    """계정 설정 검증"""
    required_fields = ['name', 'tenant_id', 'subscription_id', 'client_id', 'client_secret']
    for field in required_fields:
        if not account_info.get(field) or account_info[field] == f"your-service-principal-{field.replace('_', '-')}":
            return False, f"'{field}' 값이 설정되지 않았습니다."
    return True, "OK"

def get_backup_jobs(account_info):
    """특정 계정의 백업 작업 조회 (Service Principal 인증)"""
    try:
        print(f"\n=== {account_info['name']} 계정 처리 중... ===")
        
        # 설정 검증
        is_valid, error_msg = validate_account_config(account_info)
        if not is_valid:
            logging.error(f"{account_info['name']}: 설정 오류 - {error_msg}")
            print(f"  ❌ 설정 오류: {error_msg}")
            return []
        
        # Service Principal 인증
        credential = ClientSecretCredential(
            tenant_id=account_info['tenant_id'],
            client_id=account_info['client_id'],
            client_secret=account_info['client_secret']
        )
        
        print(f"  🔐 Service Principal 인증 중...")
        
        # Recovery Services Client 생성
        recovery_client = RecoveryServicesClient(credential, account_info['subscription_id'])
        
        # Vault 목록 조회
        print(f"  📋 Recovery Services Vault 조회 중...")
        vaults = list(recovery_client.vaults.list_by_subscription_id())
        
        if not vaults:
            logging.warning(f"{account_info['name']}: Recovery Services Vault가 없습니다.")
            print(f"  ⚠️ Recovery Services Vault가 없습니다.")
            return []
        
        print(f"  ✅ {len(vaults)}개 Vault 발견")
        
        # Backup Client 생성
        backup_client = RecoveryServicesBackupClient(credential, account_info['subscription_id'])
        
        all_jobs = []
        KST = timezone(timedelta(hours=9))
        
        for vault in vaults:
            vault_name = vault.name
            resource_group = vault.id.split('/')[4]
            
            print(f"  🔍 Vault '{vault_name}' 백업 작업 조회 중...")
            
            try:
                # 백업 작업 조회
                jobs = backup_client.backup_jobs.list(vault_name, resource_group)
                
                vault_job_count = 0
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
                    vault_job_count += 1
                
                print(f"    📊 {vault_job_count}개 백업 작업 발견")
                    
            except Exception as e:
                logging.error(f"Vault {vault_name} 백업 작업 조회 실패: {str(e)}")
                print(f"    ❌ Vault {vault_name} 조회 실패: {str(e)}")
                continue
        
        logging.info(f"{account_info['name']}: {len(all_jobs)}개 백업 작업 조회 완료")
        print(f"  ✅ 총 {len(all_jobs)}개 백업 작업 조회 완료")
        return all_jobs
        
    except AzureError as e:
        logging.error(f"{account_info['name']} Azure 오류: {str(e)}")
        print(f"  ❌ Azure 인증/권한 오류: {str(e)}")
        print(f"     Service Principal 권한을 확인하세요.")
        return []
    except Exception as e:
        logging.error(f"{account_info['name']} 처리 중 오류: {str(e)}")
        print(f"  ❌ 처리 오류: {str(e)}")
        return []

def print_summary(all_jobs):
    """결과 요약 출력"""
    print("\n" + "="*80)
    print("                   백업 모니터링 요약 결과 (Service Principal)")
    print("="*80)
    
    if not all_jobs:
        print("조회된 백업 작업이 없습니다.")
        print("\n💡 확인사항:")
        print("  - Service Principal 권한 설정")
        print("  - Recovery Services Vault 백업 정책 설정")
        print("  - 백업 대상 리소스 설정")
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
        success_rate = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"\n[{account}]")
        print(f"  총 백업 작업: {stats['total']}개")
        print(f"  성공: {stats['completed']}개 ({success_rate:.1f}%)")
        print(f"  실패: {stats['failed']}개")
    
    # 실패한 작업 상세 정보
    if failed_jobs:
        print(f"\n🚨 실패한 백업 작업 ({len(failed_jobs)}개):")
        for job in failed_jobs:
            print(f"  - {job['account_name']} | {job['vault_name']} | {job['status']} | {job['start_time']}")
    else:
        print(f"\n✅ 모든 백업 작업이 성공했습니다!")
    
    # 최근 백업 작업
    if all_jobs:
        today = datetime.now().date()
        today_jobs = [job for job in all_jobs if job['start_time_raw'] and job['start_time_raw'].date() == today]
        
        print(f"\n📅 오늘 실행된 백업 작업 ({len(today_jobs)}개):")
        if today_jobs:
            for job in today_jobs:
                status_icon = "✅" if job['status'] == 'Completed' else "❌"
                print(f"  {status_icon} {job['account_name']} | {job['vault_name']} | {job['start_time']}")
        else:
            print("  오늘 실행된 백업 작업이 없습니다.")

def main():
    """메인 실행 함수"""
    print("Azure 백업 모니터링 자동화 시스템 (Service Principal)")
    print("="*60)
    print("🔒 자동 인증 - 브라우저 팝업 없음")
    print()
    
    # 설정 파일 로드
    config = load_accounts_config()
    if not config:
        print("\n❌ 프로그램 종료: 설정 파일을 확인하세요.")
        return
    
    accounts = config.get('accounts', [])
    if not accounts:
        print("❌ 설정된 계정이 없습니다.")
        return
    
    print(f"📋 총 {len(accounts)}개 계정 처리 예정")
    
    # 모든 계정 처리
    all_jobs = []
    successful_accounts = 0
    
    for i, account in enumerate(accounts, 1):
        print(f"\n[{i}/{len(accounts)}]", end=" ")
        jobs = get_backup_jobs(account)
        if jobs is not None:  # 오류가 아닌 경우 (빈 리스트도 성공)
            all_jobs.extend(jobs)
            successful_accounts += 1
    
    # 결과 요약
    print_summary(all_jobs)
    
    print(f"\n" + "="*60)
    print(f"🎯 처리 완료: {successful_accounts}/{len(accounts)}개 계정 성공")
    print(f"🕐 실행 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📝 로그 파일: backup_monitor_sp_{datetime.now().strftime('%Y%m%d')}.log")
    print("\n💡 Service Principal 설정이 필요한 경우 README_sp.md를 참고하세요.")

if __name__ == "__main__":
    main()