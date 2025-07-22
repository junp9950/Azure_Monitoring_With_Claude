# Azure SDK 백업 모니터링 테스트

이 폴더는 Azure SDK for Python을 이용해 애저 백업 상태를 로컬에서 바로 확인하는 예제 코드가 들어 있습니다.

## 1. 준비 사항

- Python 3.x 설치
- 아래 명령어로 필요한 패키지 설치

```
pip install azure-identity azure-mgmt-recoveryservicesbackup
```

## 2. 사용 방법

1. **Azure 포털에서 구독 ID, Vault 이름, 리소스 그룹명을 확인**
2. `test_sdk_backup.py` 파일의 `subscription_id`, `vault_name`, `resource_group` 값을 본인 환경에 맞게 수정
3. 터미널(명령 프롬프트, PowerShell 등)에서 이 폴더로 이동

```
cd Azure_sdk_backupMonitoring
python test_sdk_backup.py
```

4. 처음 실행 시 브라우저가 열리며 Azure 로그인 창이 뜹니다. 로그인 후 터미널로 돌아오면 백업 작업 목록이 출력됩니다.

## 3. 참고

- Reader 권한만 있으면 조회가 가능합니다.
- 오류가 발생하면 메시지를 복사해서 질문해 주세요!
- 정상 동작하면, 이 구조를 기반으로 GUI 앱도 만들어드릴 수 있습니다 :) 