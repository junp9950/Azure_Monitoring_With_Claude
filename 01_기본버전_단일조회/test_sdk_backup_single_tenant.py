from azure.identity import InteractiveBrowserCredential
from azure.mgmt.recoveryservices import RecoveryServicesClient
from azure.mgmt.recoveryservicesbackup import RecoveryServicesBackupClient
from datetime import timezone, timedelta

# 1. 인증 (브라우저 팝업, 테넌트 지정)
tenant_id = "bd5d33c6-22d3-47ca-a5ba-c85a84243d86"
credential = InteractiveBrowserCredential(tenant_id=tenant_id)

# 2. 구독 ID 입력
subscription_id = "7289bafa-91a3-49df-bea5-c1a731a75670"

# 3. Vault 목록 조회 (구독 전체)
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