# Azure Backup Monitoring Dashboard

Azure 백업 상태와 VM 메트릭을 모니터링하는 종합 대시보드입니다.

## 📋 프로젝트 구성

### 1. 기본버전 (단일조회)
- 단일 테넌트/구독 대상 기본 백업 모니터링
- Azure SDK를 이용한 백업 작업 상태 조회

### 2. 자동화버전 (멀티계정)
- 여러 Azure 계정을 자동으로 순회하며 백업 상태 확인
- 스케줄링 기능 포함

### 3. ServicePrincipal (자동인증)
- Service Principal을 이용한 무인증 자동화
- CI/CD 파이프라인에 적합

### 4. 웹대시보드 (브라우저실행) ⭐
- **Streamlit 기반 웹 대시보드**
- VM 메트릭 실시간 모니터링
- 시각화 차트 및 알림 기능

## 🚀 빠른 시작

### 1. 필수 요구사항
- Python 3.8+
- Azure CLI 또는 Service Principal 인증
- 필요한 Python 패키지

### 2. 설치

```bash
# 저장소 클론
git clone https://github.com/junp9950/Azure_Monitoring_With_Claude.git
cd Azure_Monitoring_With_Claude

# 웹 대시보드용 패키지 설치
cd 04_웹대시보드_브라우저실행
pip install -r requirements_web.txt
```

### 3. 계정 설정

#### 3.1 계정설정 파일 생성
템플릿 파일을 복사하여 실제 계정 정보로 수정하세요:

```bash
# 기본 인증용
cp 계정설정_공통.json.template 계정설정_공통.json

# ServicePrincipal용
cp 계정설정_ServicePrincipal.json.template 계정설정_ServicePrincipal.json
```

#### 3.2 Azure 정보 입력

**계정설정_공통.json** 파일을 열어 다음 정보를 입력:

```json
{
  "accounts": [
    {
      "name": "Production_Account",
      "type": "azure",
      "tenant_id": "실제-테넌트-ID",
      "subscription_id": "실제-구독-ID", 
      "description": "Production Environment"
    }
  ]
}
```

#### 3.3 Azure 정보 찾는 방법

**Azure Portal에서:**
1. **Tenant ID**: Azure Active Directory → 속성 → 테넌트 ID
2. **Subscription ID**: 구독 → 구독 ID 복사

**Azure CLI로:**
```bash
# 로그인
az login

# 계정 정보 확인
az account show
```

### 4. 웹 대시보드 실행

```bash
cd 04_웹대시보드_브라우저실행
streamlit run backup_monitor_web.py
```

또는 배치 파일 실행:
```bash
run_web_app.bat
```

브라우저에서 `http://localhost:8501`로 접속

## 🔧 기능별 사용법

### 웹 대시보드 주요 기능
- **실시간 VM 상태 모니터링**
- **백업 작업 상태 추적**
- **CPU/메모리/디스크 메트릭 시각화**
- **다중 계정 지원**
- **알림 및 필터링 기능**

### 사이드바 옵션
- **계정 선택**: 모니터링할 Azure 계정 선택
- **메트릭 수집**: VM 성능 메트릭 수집 여부 (API 비용 발생)
- **새로고침**: 수동 데이터 갱신

## 💰 Azure Monitor API 비용

Azure Monitor Metrics API 사용 시 비용이 발생할 수 있습니다:

- **무료 할당량**: 월 1,000,000 API 호출
- **초과 시 요금**: $0.01 / 1,000 API 호출
- **일반적인 사용량**: 무료 범위 내에서 충분

**비용 절약 팁:**
- 사이드바에서 "메트릭 수집" 해제
- 필요한 계정만 선택하여 모니터링

## 🔐 보안 주의사항

- `계정설정_*.json` 파일은 민감한 정보를 포함하므로 **절대 Git에 커밋하지 마세요**
- `.gitignore`에 이미 제외 설정되어 있음
- Service Principal 사용 시 최소 권한 원칙 적용

## 🛠️ 문제 해결

### 일반적인 오류

**1. ModuleNotFoundError: No module named 'azure.mgmt.compute'**
```bash
pip install azure-mgmt-compute azure-identity streamlit
```

**2. 인증 실패**
- Azure CLI 로그인 확인: `az login`
- 계정설정 파일의 tenant_id, subscription_id 확인

**3. VM 정보 조회 실패**
- Azure 구독에 대한 읽기 권한 확인
- VM이 실제로 존재하는지 확인

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 제공됩니다.

## 🤝 기여

버그 리포트, 기능 요청, Pull Request 환영합니다!

## 📞 지원

문제가 있으시면 GitHub Issues를 통해 문의해주세요.