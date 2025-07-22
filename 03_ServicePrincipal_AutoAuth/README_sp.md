# Azure 백업 모니터링 자동화 시스템 (Service Principal)

🔒 **브라우저 팝업 없이 완전 자동화된 멀티 계정 백업 모니터링 도구**

MFA와 브라우저 인증 없이 Service Principal을 사용하여 자동으로 여러 Azure 계정의 백업 상태를 모니터링합니다.

## 🆚 기존 버전과의 차이점

| 구분 | 기존 버전 | Service Principal 버전 |
|------|-----------|----------------------|
| **인증 방식** | 브라우저 팝업 + MFA | Service Principal (자동) |
| **사용 편의성** | 매번 로그인 필요 | 한 번 설정 후 자동 실행 |
| **자동화 적합성** | 부적합 (수동 개입) | 완전 자동화 가능 |
| **보안성** | 개인 계정 | 제한된 권한의 앱 계정 |

## 🚀 빠른 시작

### 1단계: Service Principal 생성

**Azure Portal에서 앱 등록:**

1. **Azure Portal** → **Azure Active Directory** → **앱 등록** → **새 등록**
2. **이름**: `BackupMonitoringApp` (원하는 이름)
3. **지원되는 계정 유형**: `이 조직 디렉터리의 계정만`
4. **등록** 클릭

### 2단계: 클라이언트 시크릿 생성

1. 생성된 앱 → **인증서 및 비밀** → **새 클라이언트 비밀**
2. **설명**: `BackupMonitoring` 
3. **만료**: `24개월` (권장)
4. **추가** 클릭
5. ⚠️ **생성된 시크릿 값을 바로 복사** (나중에 다시 볼 수 없음)

### 3단계: 필요한 정보 수집

앱 등록 페이지에서 다음 정보를 복사:

- **애플리케이션(클라이언트) ID**: `client_id`로 사용
- **디렉터리(테넌트) ID**: `tenant_id`로 사용
- **클라이언트 시크릿 값**: `client_secret`로 사용
- **구독 ID**: Azure Portal → 구독에서 확인

### 4단계: 권한 부여

**각 구독에서 Service Principal에 권한 부여:**

1. **Azure Portal** → **구독** → 해당 구독 선택
2. **액세스 제어(IAM)** → **역할 할당 추가**
3. **역할**: `Reader` 또는 `Backup Reader`
4. **다음** → **구성원 선택** → 생성한 앱 이름 검색
5. **검토 + 할당**

### 5단계: 설정 파일 편집

`accounts_config_sp.json` 파일을 열어서 실제 값으로 수정:

```json
{
  "accounts": [
    {
      "name": "NH_Logistics_Parcel",
      "tenant_id": "실제-테넌트-ID",
      "subscription_id": "실제-구독-ID",
      "client_id": "실제-클라이언트-ID",
      "client_secret": "실제-클라이언트-시크릿",
      "description": "택배 계정"
    },
    {
      "name": "NH_Logistics_TMS",
      "tenant_id": "실제-테넌트-ID",
      "subscription_id": "실제-구독-ID",
      "client_id": "실제-클라이언트-ID",
      "client_secret": "실제-클라이언트-시크릿",
      "description": "TMS 계정"
    }
  ]
}
```

### 6단계: 실행

```bash
# 배치 파일로 실행 (권장)
run_backup_check_sp.bat

# 또는 직접 실행
python backup_monitor_sp.py
```

## 📊 실행 결과 예시

```
Azure 백업 모니터링 자동화 시스템 (Service Principal)
============================================================
🔒 자동 인증 - 브라우저 팝업 없음

📋 총 2개 계정 처리 예정

[1/2] === NH_Logistics_Parcel 계정 처리 중... ===
  🔐 Service Principal 인증 중...
  📋 Recovery Services Vault 조회 중...
  ✅ 1개 Vault 발견
  🔍 Vault 'rs-jeewoong-test' 백업 작업 조회 중...
    📊 0개 백업 작업 발견
  ✅ 총 0개 백업 작업 조회 완료

[2/2] === NH_Logistics_TMS 계정 처리 중... ===
  🔐 Service Principal 인증 중...
  📋 Recovery Services Vault 조회 중...
  ✅ 1개 Vault 발견
  🔍 Vault 'RSV-NHTMS' 백업 작업 조회 중...
    📊 35개 백업 작업 발견
  ✅ 총 35개 백업 작업 조회 완료

================================================================================
                   백업 모니터링 요약 결과 (Service Principal)
================================================================================

[NH_Logistics_TMS]
  총 백업 작업: 35개
  성공: 35개 (100.0%)
  실패: 0개

✅ 모든 백업 작업이 성공했습니다!

📅 오늘 실행된 백업 작업 (5개):
  ✅ NH_Logistics_TMS | RSV-NHTMS | 2025-07-17 03:09:17
  ✅ NH_Logistics_TMS | RSV-NHTMS | 2025-07-17 03:05:41
  ...

============================================================
🎯 처리 완료: 2/2개 계정 성공
🕐 실행 완료: 2025-07-17 17:30:15
📝 로그 파일: backup_monitor_sp_20250717.log
```

## 🔧 문제 해결

### 인증 오류

**오류**: `AuthenticationFailed` 또는 `Unauthorized`

**해결 방법**:
1. Service Principal 정보가 정확한지 확인
2. 클라이언트 시크릿이 만료되지 않았는지 확인
3. 테넌트 ID가 정확한지 확인

### 권한 오류

**오류**: `Forbidden` 또는 권한 관련 오류

**해결 방법**:
1. 구독에서 Service Principal에 Reader 권한 부여 확인
2. Recovery Services Vault에 대한 접근 권한 확인

### 설정 파일 오류

**오류**: `파일을 찾을 수 없습니다` 또는 `JSON 형식 오류`

**해결 방법**:
1. `accounts_config_sp.json` 파일이 존재하는지 확인
2. JSON 형식이 올바른지 확인 (쉼표, 괄호 등)
3. 모든 필수 필드가 입력되었는지 확인

## 🔐 보안 고려사항

### 클라이언트 시크릿 관리
- ⚠️ **클라이언트 시크릿을 안전하게 보관**
- 정기적으로 시크릿 교체 (권장: 6개월~1년)
- 소스 코드에 시크릿 하드코딩 금지

### 권한 최소화
- Service Principal에 필요한 최소 권한만 부여
- `Reader` 권한으로 충분 (백업 조회만 필요)
- 불필요한 구독에 권한 부여 금지

### 파일 보안
- `accounts_config_sp.json` 파일을 안전한 위치에 저장
- 파일 접근 권한 제한
- 버전 관리 시스템에 업로드 금지

## 🕐 스케줄링 설정

**Windows 작업 스케줄러로 자동 실행:**

1. **작업 스케줄러** 실행
2. **기본 작업 만들기**
3. **이름**: `Azure 백업 모니터링`
4. **트리거**: `매일` (원하는 시간 설정)
5. **작업**: `프로그램 시작`
6. **프로그램/스크립트**: `run_backup_check_sp.bat`의 전체 경로
7. **시작 위치**: 배치 파일이 있는 폴더 경로

## 💡 추가 기능 아이디어

- [ ] **이메일 알림**: 실패한 백업 작업 발생 시 이메일 전송
- [ ] **Slack/Teams 알림**: 메신저로 결과 전송
- [ ] **Excel 리포트**: 상세한 백업 리포트 생성
- [ ] **대시보드**: 웹 기반 모니터링 대시보드
- [ ] **성능 모니터링**: 백업 소요 시간 추적

## 📚 관련 링크

- [Azure Service Principal 문서](https://docs.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals)
- [Azure Backup REST API](https://docs.microsoft.com/en-us/rest/api/backup/)
- [Azure Python SDK 문서](https://docs.microsoft.com/en-us/python/api/overview/azure/)

---

**문의사항이나 개선 제안이 있으시면 언제든지 말씀해 주세요!**