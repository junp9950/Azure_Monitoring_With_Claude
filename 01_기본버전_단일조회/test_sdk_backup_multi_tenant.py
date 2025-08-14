import subprocess
import json
from azure.identity import InteractiveBrowserCredential

# YAML 모듈 자동 설치
try:
    import yaml
except ImportError:
    print("PyYAML 패키지를 설치 중입니다...")
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyYAML>=6.0"])
    import yaml
    print("PyYAML 설치 완료!")
from azure.mgmt.recoveryservices import RecoveryServicesClient
from azure.mgmt.recoveryservicesbackup import RecoveryServicesBackupClient
from datetime import timezone, timedelta

# az.cmd 전체 경로 지정
AZ_PATH = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"

# 1. az CLI로 테넌트 목록 조회
result = subprocess.run(
    [AZ_PATH, "account", "tenant", "list", "--output", "json"],
    capture_output=True, text=True, encoding="utf-8"
)
tenants = json.loads(result.stdout)

print("=== 내 계정의 테넌트 목록 ===")
for idx, t in enumerate(tenants):
    print(f"{idx+1}. {t.get('displayName', '')} ({t['tenantId']})")

choice = int(input("조회할 테넌트 번호를 입력하세요: ")) - 1
tenant_id = tenants[choice]['tenantId']

# 2. 해당 테넌트로 인증
credential = InteractiveBrowserCredential(tenant_id=tenant_id)

# 3. 구독 목록 조회 (az CLI 사용)
result = subprocess.run(
    [AZ_PATH, "account", "list", "--all", "--output", "json", "--tenant", tenant_id],
    capture_output=True, text=True, encoding="utf-8"
)
subscriptions = json.loads(result.stdout)

print("=== 선택한 테넌트의 구독 목록 ===")
for idx, s in enumerate(subscriptions):
    print(f"{idx+1}. {s['name']} ({s['id']})")

choice = int(input("조회할 구독 번호를 입력하세요: ")) - 1
subscription_id = subscriptions[choice]['id']

# 4. Vault 목록 조회 (SDK)
recovery_client = RecoveryServicesClient(credential, subscription_id)
vaults = list(recovery_client.vaults.list_by_subscription_id())

if not vaults:
    print("이 구독에 Recovery Services Vault가 없습니다.")
    exit(1)

print("=== 구독 내 Recovery Services Vault 목록 ===")
for idx, v in enumerate(vaults):
    resource_group = v.id.split('/')[4]
    print(f"{idx+1}. Vault 이름: {v.name}, 리소스 그룹: {resource_group}")

choice = int(input("조회할 Vault 번호를 입력하세요: ")) - 1
vault = vaults[choice]
vault_name = vault.name
resource_group = vault.id.split('/')[4]

backup_client = RecoveryServicesBackupClient(credential, subscription_id)
jobs = backup_client.backup_jobs.list(vault_name, resource_group)

KST = timezone(timedelta(hours=9))
print(f"=== {vault_name} 백업 작업 목록 (KST) ===")
for job in jobs:
    start_utc = job.properties.start_time
    start_kst = start_utc.astimezone(KST) if start_utc else None
    print(f"Job: {job.name}, Status: {job.properties.status}, Start: {start_kst.strftime('%Y-%m-%d %H:%M:%S') if start_kst else 'N/A'}") 