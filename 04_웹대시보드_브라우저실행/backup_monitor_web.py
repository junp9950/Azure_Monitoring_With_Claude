import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta
from azure.identity import InteractiveBrowserCredential
from azure.mgmt.recoveryservices import RecoveryServicesClient
from azure.mgmt.recoveryservicesbackup import RecoveryServicesBackupClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.core.exceptions import AzureError
import time

# 페이지 설정
st.set_page_config(
    page_title="클라우드 인프라 모니터링 대시보드",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 개선된 UI 스타일
st.markdown("""
<style>
    /* 사이드바 스타일 개선 */
    .stSidebar {
        background-color: #2e3440 !important;
        color: white !important;
    }
    
    .stSidebar .stSelectbox label, 
    .stSidebar .stMultiSelect label,
    .stSidebar .stCheckbox label,
    .stSidebar .stButton > button,
    .stSidebar h1, .stSidebar h2, .stSidebar h3,
    .stSidebar .stMarkdown {
        color: white !important;
        font-weight: 600 !important;
    }
    
    .stSidebar .stSelectbox > div > div,
    .stSidebar .stMultiSelect > div > div {
        background-color: #3b4252 !important;
        color: white !important;
        border: 1px solid #4c566a !important;
    }
    
    .stSidebar .stButton > button {
        background-color: #5e81ac !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        padding: 0.75rem 1.5rem !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
    }
    
    .stSidebar .stButton > button:hover {
        background-color: #81a1c1 !important;
        transform: translateY(-1px) !important;
    }
    
    /* 메인 콘텐츠 스타일 */
    .main .block-container {
        padding-top: 2rem !important;
    }
    
    /* 성공/실패 상태 스타일 */
    .backup-status-success {
        background-color: #d4edda;
        color: #155724;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #28a745;
        margin: 10px 0;
        font-weight: 600;
    }
    
    .backup-status-failed {
        background-color: #f8d7da;
        color: #721c24;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #dc3545;
        margin: 10px 0;
        font-weight: 600;
    }
    
    /* 메트릭 카드 스타일 */
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        margin: 15px 0;
    }
    
    /* 진행 상황 스타일 */
    .stProgress > div > div {
        background-color: #5e81ac !important;
    }
    
    /* 알림창 스타일 개선 */
    .stAlert {
        border-radius: 8px !important;
        padding: 15px !important;
        font-weight: 600 !important;
    }
    
    /* 테이블 스타일 개선 */
    .stDataFrame {
        border-radius: 10px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
    }
    
    .stDataFrame table {
        border-collapse: separate !important;
        border-spacing: 0 !important;
        font-size: 14px !important;
    }
    
    .stDataFrame thead th {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        font-weight: bold !important;
        padding: 12px 8px !important;
        text-align: center !important;
        border: none !important;
    }
    
    .stDataFrame tbody td {
        padding: 10px 8px !important;
        border-bottom: 1px solid #e0e0e0 !important;
        text-align: center !important;
    }
    
    .stDataFrame tbody tr:hover {
        background-color: #f8f9fa !important;
        transform: scale(1.01) !important;
        transition: all 0.2s ease !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_accounts_config():
    """계정 설정 파일 로드 (캐시됨)"""
    try:
        with open('../계정설정_공통.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("❌ 계정설정_공통.json 파일을 찾을 수 없습니다.")
        return None
    except json.JSONDecodeError:
        st.error("❌ 설정 파일 형식이 올바르지 않습니다.")
        return None

# Azure VM 모니터링 함수들
def get_vm_24h_metrics(account_info, vm_list, progress_bar, status_text):
    """VM의 24시간 메트릭 추이 데이터 수집"""
    try:
        credential = InteractiveBrowserCredential(tenant_id=account_info['tenant_id'])
        monitor_client = MonitorManagementClient(credential, account_info['subscription_id'])
        
        # 24시간 전부터 현재까지
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        vm_trends = {}
        
        for idx, vm in enumerate(vm_list):
            if vm['power_state'] != 'VM running':
                continue
                
            try:
                progress = idx / len(vm_list) 
                progress_bar.progress(progress)
                status_text.text(f"📈 VM '{vm['vm_name']}' 24시간 추이 수집 중... ({idx+1}/{len(vm_list)})")
                
                vm_id = f"/subscriptions/{account_info['subscription_id']}/resourceGroups/{vm['resource_group']}/providers/Microsoft.Compute/virtualMachines/{vm['vm_name']}"
                
                # CPU 메트릭 (24시간)
                cpu_metrics = monitor_client.metrics.list(
                    resource_uri=vm_id,
                    timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                    interval='PT1H',  # 1시간 간격
                    metricnames='Percentage CPU',
                    aggregation='Average'
                )
                
                cpu_data = []
                if cpu_metrics.value and cpu_metrics.value[0].timeseries:
                    for data_point in cpu_metrics.value[0].timeseries[0].data:
                        if data_point.average is not None:
                            cpu_data.append({
                                'timestamp': data_point.time_stamp,
                                'value': data_point.average
                            })
                
                # 디스크 읽기 메트릭 (24시간)
                disk_metrics = monitor_client.metrics.list(
                    resource_uri=vm_id,
                    timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                    interval='PT1H',
                    metricnames='Disk Read Bytes',
                    aggregation='Total'
                )
                
                disk_data = []
                if disk_metrics.value and disk_metrics.value[0].timeseries:
                    for data_point in disk_metrics.value[0].timeseries[0].data:
                        if data_point.total is not None:
                            disk_data.append({
                                'timestamp': data_point.time_stamp,
                                'value': data_point.total / (1024**2)  # MB로 변환
                            })
                
                vm_trends[vm['vm_name']] = {
                    'cpu_trend': cpu_data,
                    'disk_trend': disk_data,
                    'account_name': vm['account_name'],
                    'resource_group': vm['resource_group']
                }
                
                time.sleep(0.2)  # API 레이트 리미트 방지
                
            except Exception as vm_error:
                st.warning(f"⚠️ VM '{vm['vm_name']}' 24시간 메트릭 수집 실패: {str(vm_error)[:100]}...")
                continue
        
        progress_bar.progress(1.0)
        status_text.text(f"✅ 24시간 추이 데이터 수집 완료!")
        return vm_trends
        
    except Exception as e:
        st.error(f"🚨 24시간 메트릭 수집 오류: {str(e)}")
        return {}

def get_azure_vms(account_info, progress_bar, status_text, collect_metrics=True):
    """Azure VM 목록, 상태 및 메트릭 조회"""
    try:
        status_text.text(f"🔐 {account_info['name']} Azure 인증 중...")
        progress_bar.progress(0.1)
        
        # Azure 인증
        credential = InteractiveBrowserCredential(tenant_id=account_info['tenant_id'])
        compute_client = ComputeManagementClient(credential, account_info['subscription_id'])
        monitor_client = MonitorManagementClient(credential, account_info['subscription_id']) if collect_metrics else None
        
        status_text.text(f"🖥️ {account_info['name']} VM 목록 조회 중...")
        progress_bar.progress(0.2)
        
        # VM 목록 조회
        vm_list = list(compute_client.virtual_machines.list_all())
        vms = []
        KST = timezone(timedelta(hours=9))
        
        for idx, vm in enumerate(vm_list):
            try:
                # 진행률 업데이트
                vm_progress = 0.2 + (0.6 * idx / len(vm_list))  # 20%에서 80%까지
                progress_bar.progress(vm_progress)
                status_text.text(f"🔍 VM '{vm.name}' 정보 수집 중... ({idx+1}/{len(vm_list)})")
                
                # VM 상세 정보 조회
                vm_detail = compute_client.virtual_machines.get(
                    vm.id.split('/')[4],  # resource_group
                    vm.name,
                    expand='instanceView'
                )
                
                # VM 상태 추출
                power_state = 'Unknown'
                provisioning_state = 'Unknown'
                
                if vm_detail.instance_view and vm_detail.instance_view.statuses:
                    for status in vm_detail.instance_view.statuses:
                        if status.code.startswith('PowerState/'):
                            power_state = status.display_status
                        elif status.code.startswith('ProvisioningState/'):
                            provisioning_state = status.display_status
                
                vm_info = {
                    'account_name': account_info['name'],
                    'vm_name': vm.name,
                    'resource_group': vm.id.split('/')[4],
                    'location': vm.location,
                    'vm_size': vm_detail.hardware_profile.vm_size if vm_detail.hardware_profile else 'N/A',
                    'power_state': power_state,
                    'provisioning_state': provisioning_state,
                    'private_ip': 'N/A',  # 간소화
                    'os_type': str(vm_detail.storage_profile.os_disk.os_type) if vm_detail.storage_profile and vm_detail.storage_profile.os_disk and vm_detail.storage_profile.os_disk.os_type else 'N/A',
                    'cpu_usage': 'N/A',
                    'memory_usage': 'N/A',
                    'disk_usage': 'N/A'
                }
                
                # 메트릭 수집 (실행 중인 VM만)
                if collect_metrics and monitor_client and power_state == 'VM running':
                    try:
                        status_text.text(f"📊 VM '{vm.name}' 메트릭 수집 중...")
                        
                        # 최근 5분간 메트릭 조회
                        end_time = datetime.utcnow()
                        start_time = end_time - timedelta(minutes=5)
                        
                        # CPU 사용률
                        try:
                            cpu_metrics = monitor_client.metrics.list(
                                resource_uri=vm.id,
                                timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                                interval='PT1M',
                                metricnames='Percentage CPU',
                                aggregation='Average'
                            )
                            
                            if cpu_metrics.value and cpu_metrics.value[0].timeseries:
                                cpu_data = cpu_metrics.value[0].timeseries[0].data
                                if cpu_data:
                                    vm_info['cpu_usage'] = f"{cpu_data[-1].average:.1f}%" if cpu_data[-1].average else 'N/A'
                        except Exception as cpu_error:
                            vm_info['cpu_usage'] = 'Error'
                        
                        # 사용 가능한 메모리 (Windows VM만)
                        try:
                            if vm_info['os_type'].lower() == 'windows':
                                memory_metrics = monitor_client.metrics.list(
                                    resource_uri=vm.id,
                                    timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                                    interval='PT1M',
                                    metricnames='Available Memory Bytes',
                                    aggregation='Average'
                                )
                                
                                if memory_metrics.value and memory_metrics.value[0].timeseries:
                                    memory_data = memory_metrics.value[0].timeseries[0].data
                                    if memory_data and memory_data[-1].average:
                                        available_gb = memory_data[-1].average / (1024**3)
                                        vm_info['memory_usage'] = f"{available_gb:.1f}GB 사용 가능"
                            else:
                                vm_info['memory_usage'] = 'Linux 메트릭 제한'
                        except Exception as memory_error:
                            vm_info['memory_usage'] = 'Error'
                        
                        # 디스크 읽기/쓰기 
                        try:
                            disk_read_metrics = monitor_client.metrics.list(
                                resource_uri=vm.id,
                                timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                                interval='PT1M',
                                metricnames='Disk Read Bytes',
                                aggregation='Total'
                            )
                            
                            if disk_read_metrics.value and disk_read_metrics.value[0].timeseries:
                                disk_data = disk_read_metrics.value[0].timeseries[0].data
                                if disk_data and disk_data[-1].total:
                                    disk_mb = disk_data[-1].total / (1024**2)
                                    vm_info['disk_usage'] = f"{disk_mb:.1f}MB/min 읽기"
                        except Exception as disk_error:
                            vm_info['disk_usage'] = 'Error'
                        
                        time.sleep(0.1)  # API 호출 간격 조절
                        
                    except Exception as metric_error:
                        st.warning(f"⚠️ VM '{vm.name}' 메트릭 수집 실패: {str(metric_error)[:100]}...")
                        # 메트릭 수집 실패 시 기본값 유지
                
                vms.append(vm_info)
                
            except Exception as vm_error:
                st.warning(f"⚠️ VM '{vm.name}' 정보 조회 실패: {str(vm_error)[:100]}...")
                continue
        
        progress_bar.progress(1.0)
        metrics_note = " (메트릭 포함)" if collect_metrics else " (기본 정보만)"
        status_text.text(f"✅ {account_info['name']}: {len(vms)}개 Azure VM 조회 완료{metrics_note}")
        return vms
        
    except AzureError as e:
        error_msg = str(e)
        st.error(f"🚨 {account_info['name']} Azure VM 조회 오류")
        st.error(f"📋 오류 내용: {error_msg}")
        
        if "authentication" in error_msg.lower():
            st.error("💡 해결방법: 브라우저에서 Azure 로그인을 다시 시도하세요.")
        elif "forbidden" in error_msg.lower() or "unauthorized" in error_msg.lower():
            st.error("💡 해결방법: Azure 구독에 대한 Reader 권한을 확인하세요.")
        else:
            st.error("💡 해결방법: 1) Azure 로그인 재시도 2) 권한 확인 3) 네트워크 연결 확인")
        
        return []
    except Exception as e:
        st.error(f"🚨 {account_info['name']} 예상치 못한 오류 - {str(e)}")
        return []

def get_backup_jobs(account_info, progress_bar, status_text):
    """특정 계정의 백업 작업 조회 (개선된 오류 처리 및 타임아웃)"""
    import threading
    import queue
    
    def fetch_data():
        """별도 스레드에서 데이터 조회"""
        try:
            # 인증
            credential = InteractiveBrowserCredential(
                tenant_id=account_info['tenant_id'],
                timeout=60  # 1분 타임아웃
            )
            
            # Recovery Services Client 생성
            recovery_client = RecoveryServicesClient(credential, account_info['subscription_id'])
            
            # Vault 목록 조회 (타임아웃 적용)
            import signal
            def timeout_handler(signum, frame):
                raise TimeoutError("Vault 조회 시간 초과")
            
            try:
                # 비동기 방식으로 처리
                vaults = list(recovery_client.vaults.list_by_subscription_id())
                return {"success": True, "vaults": vaults}
            except Exception as e:
                return {"success": False, "error": str(e)}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    try:
        status_text.text(f"🔐 {account_info['name']} 인증 중...")
        progress_bar.progress(0.1)
        time.sleep(0.5)  # UI 업데이트를 위한 짧은 대기
        
        status_text.text(f"📋 {account_info['name']} Recovery Services Vault 조회 중...")
        status_text.text(f"⏱️ 최대 60초까지 소요될 수 있습니다...")
        progress_bar.progress(0.2)
        
        # 타임아웃을 적용한 데이터 조회
        start_time = time.time()
        max_wait_time = 60  # 60초 타임아웃
        
        try:
            # 인증 및 클라이언트 생성
            credential = InteractiveBrowserCredential(tenant_id=account_info['tenant_id'])
            recovery_client = RecoveryServicesClient(credential, account_info['subscription_id'])
            
            # 진행상황 업데이트
            progress_bar.progress(0.4)
            status_text.text(f"🔍 {account_info['name']} Vault 목록 가져오는 중...")
            
            # Vault 목록 조회
            vaults = []
            try:
                vaults = list(recovery_client.vaults.list_by_subscription_id())
                elapsed_time = time.time() - start_time
                status_text.text(f"✅ Vault 조회 완료 ({elapsed_time:.1f}초 소요)")
            except Exception as vault_error:
                status_text.text(f"❌ Vault 조회 실패: {str(vault_error)}")
                st.error(f"🚨 {account_info['name']}: Vault 조회 실패")
                st.error(f"📋 오류 내용: {str(vault_error)}")
                st.error(f"💡 해결방법: 1) Azure 권한 확인 2) 네트워크 연결 확인 3) 구독 ID 확인")
                return []
            
            if not vaults:
                st.warning(f"⚠️ {account_info['name']}: Recovery Services Vault가 없습니다.")
                status_text.text(f"📋 {account_info['name']}: Vault 없음")
                return []
            
            progress_bar.progress(0.6)
            status_text.text(f"🔍 {account_info['name']}: {len(vaults)}개 Vault에서 백업 작업 조회 중...")
            
            # Backup Client 생성
            backup_client = RecoveryServicesBackupClient(credential, account_info['subscription_id'])
            
            all_jobs = []
            KST = timezone(timedelta(hours=9))
            
            for i, vault in enumerate(vaults):
                vault_name = vault.name
                resource_group = vault.id.split('/')[4]
                
                try:
                    status_text.text(f"📊 Vault '{vault_name}' 백업 작업 조회 중... ({i+1}/{len(vaults)})")
                    
                    # 백업 작업 조회
                    jobs = backup_client.backup_jobs.list(vault_name, resource_group)
                    
                    vault_job_count = 0
                    for job in jobs:
                        start_utc = job.properties.start_time
                        end_utc = job.properties.end_time
                        start_kst = start_utc.astimezone(KST) if start_utc else None
                        end_kst = end_utc.astimezone(KST) if end_utc else None
                        
                        # 소요 시간 계산
                        duration = None
                        if start_kst and end_kst:
                            duration_seconds = (end_kst - start_kst).total_seconds()
                            if duration_seconds > 0:
                                hours = int(duration_seconds // 3600)
                                minutes = int((duration_seconds % 3600) // 60)
                                if hours > 0:
                                    duration = f"{hours}시간 {minutes}분"
                                else:
                                    duration = f"{minutes}분"
                        
                        job_info = {
                            'account_name': account_info['name'],
                            'vault_name': vault_name,
                            'job_id': job.name,
                            'status': job.properties.status,
                            'start_time': start_kst.strftime('%Y-%m-%d %H:%M:%S') if start_kst else 'N/A',
                            'end_time': end_kst.strftime('%Y-%m-%d %H:%M:%S') if end_kst else 'N/A',
                            'duration': duration if duration else 'N/A',
                            'start_time_raw': start_kst,
                            'end_time_raw': end_kst,
                            'resource_group': resource_group
                        }
                        all_jobs.append(job_info)
                        vault_job_count += 1
                    
                    # 진행률 업데이트
                    progress = 0.6 + (0.3 * (i + 1) / len(vaults))
                    progress_bar.progress(progress)
                    
                    status_text.text(f"✅ Vault '{vault_name}': {vault_job_count}개 작업 발견")
                    time.sleep(0.2)  # UI 업데이트를 위한 짧은 대기
                        
                except Exception as vault_error:
                    st.warning(f"⚠️ Vault '{vault_name}' 조회 실패: {str(vault_error)}")
                    continue
            
            progress_bar.progress(1.0)
            total_time = time.time() - start_time
            status_text.text(f"🎉 {account_info['name']}: {len(all_jobs)}개 백업 작업 조회 완료! ({total_time:.1f}초 소요)")
            return all_jobs
            
        except TimeoutError:
            st.error(f"⏰ {account_info['name']}: 조회 시간 초과 (60초)")
            st.error("💡 네트워크가 느리거나 Vault가 많을 수 있습니다. 잠시 후 다시 시도해주세요.")
            return []
        
    except AzureError as e:
        error_msg = str(e)
        st.error(f"🚨 {account_info['name']} Azure 인증/권한 오류")
        st.error(f"📋 오류 내용: {error_msg}")
        
        # 일반적인 오류에 대한 해결 방법 제시
        if "authentication" in error_msg.lower():
            st.error("💡 해결방법: 브라우저에서 Azure 로그인을 다시 시도하세요.")
        elif "forbidden" in error_msg.lower() or "unauthorized" in error_msg.lower():
            st.error("💡 해결방법: Azure 구독에 대한 Reader 권한을 확인하세요.")
        else:
            st.error("💡 해결방법: 1) Azure 로그인 재시도 2) 권한 확인 3) 네트워크 연결 확인")
        
        return []
        
    except Exception as e:
        st.error(f"🚨 {account_info['name']} 예상치 못한 오류 발생")
        st.error(f"📋 오류 내용: {str(e)}")
        st.error("💡 해결방법: 페이지를 새로고침하거나 잠시 후 다시 시도해주세요.")
        return []

def create_summary_charts(df):
    """요약 차트 생성"""
    if df.empty:
        st.info("📊 표시할 데이터가 없습니다.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 계정별 백업 작업 수
        account_counts = df.groupby('account_name').size().reset_index(name='count')
        fig1 = px.bar(
            account_counts, 
            x='account_name', 
            y='count',
            title='📊 계정별 백업 작업 수',
            color='count',
            color_continuous_scale='Blues'
        )
        fig1.update_layout(showlegend=False)
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # 상태별 백업 작업 분포
        status_counts = df['status'].value_counts().reset_index()
        status_counts.columns = ['status', 'count']
        
        colors = {'Completed': '#28a745', 'Failed': '#dc3545', 'InProgress': '#ffc107'}
        fig2 = px.pie(
            status_counts, 
            values='count', 
            names='status',
            title='📈 백업 상태 분포',
            color='status',
            color_discrete_map=colors
        )
        st.plotly_chart(fig2, use_container_width=True)

def display_metrics(df):
    """주요 지표 표시"""
    if df.empty:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_jobs = len(df)
    completed_jobs = len(df[df['status'] == 'Completed'])
    failed_jobs = len(df[df['status'].isin(['Failed', 'Cancelled'])])
    success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
    
    with col1:
        st.metric("총 백업 작업", total_jobs)
    
    with col2:
        st.metric("성공한 작업", completed_jobs, f"{success_rate:.1f}%")
    
    with col3:
        st.metric("실패한 작업", failed_jobs)
    
    with col4:
        today = datetime.now().date()
        today_jobs = len(df[df['start_time_raw'].dt.date == today]) if 'start_time_raw' in df.columns else 0
        st.metric("오늘 실행", today_jobs)

def display_vm_monitoring():
    """Azure VM 모니터링 화면"""
    st.subheader("🖥️ Azure VM 인스턴스 모니터링")
    
    # 설정 파일 로드
    config = load_accounts_config()
    if not config:
        return
    
    accounts = config.get('accounts', [])
    if not accounts:
        st.warning("⚠️ 설정된 Azure 계정이 없습니다.")
        st.info("💡 계정설정_공통.json 파일에 Azure 계정 정보를 추가하세요.")
        return
    
    # Azure 계정 선택
    account_names = [acc['name'] for acc in accounts]
    selected_accounts = st.multiselect(
        "🏢 모니터링할 Azure 계정 선택",
        account_names,
        default=account_names,
        help="VM 상태를 확인할 Azure 계정을 선택하세요"
    )
    
    # 메트릭 수집 옵션
    col_option1, col_option2 = st.columns(2)
    
    with col_option1:
        collect_metrics = st.checkbox("📊 실시간 메트릭 수집", 
                                     value=True, 
                                     help="VM의 현재 CPU, Memory, Disk 사용률을 수집합니다.")
    
    with col_option2:
        collect_trends = st.checkbox("📈 24시간 추이 데이터 수집", 
                                    value=False, 
                                    help="VM의 24시간 메트릭 추이를 수집합니다. 시간이 오래 걸립니다.")
    
    if collect_metrics or collect_trends:
        if collect_trends:
            st.warning("⚠️ 24시간 추이 데이터 수집은 시간이 오래 걸리며 API 비용이 발생할 수 있습니다.")
        else:
            st.info("💡 메트릭 수집은 실행 중인 VM에 대해서만 진행됩니다.")
    
    # VM 조회 버튼
    if st.button("🚀 Azure VM 상태 조회", type="primary"):
        if not selected_accounts:
            st.warning("⚠️ 최소 하나의 Azure 계정을 선택해주세요.")
            return
        
        # 선택된 계정 필터링
        selected_configs = [acc for acc in accounts if acc['name'] in selected_accounts]
        
        # 진행상황 표시
        st.subheader("🔄 Azure VM 모니터링 진행 중...")
        
        # 전체 진행률 표시
        overall_progress = st.progress(0)
        overall_status = st.empty()
        
        all_vms = []
        total_accounts = len(selected_configs)
        
        for i, account in enumerate(selected_configs):
            # 계정별 섹션
            with st.expander(f"☁️ [{i+1}/{total_accounts}] {account['name']}", expanded=True):
                
                # 개별 계정 진행상황
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # 계정 정보 표시
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**구독 ID:** {account['subscription_id'][:8]}...")
                with col2:
                    st.write(f"**테넌트 ID:** {account['tenant_id'][:8]}...")
                
                # 작업 시작 시간 기록
                start_time = time.time()
                
                vms = get_azure_vms(account, progress_bar, status_text, collect_metrics)
                all_vms.extend(vms)
                
                # 작업 완료 시간 계산
                elapsed_time = time.time() - start_time
                
                # 결과 요약 표시
                if vms:
                    st.success(f"✅ {len(vms)}개 Azure VM 조회 완료 ({elapsed_time:.1f}초 소요)")
                else:
                    st.info(f"ℹ️ Azure VM 없음 ({elapsed_time:.1f}초 소요)")
            
            # 전체 진행률 업데이트
            overall_progress_value = (i + 1) / total_accounts
            overall_progress.progress(overall_progress_value)
            overall_status.text(f"🔄 {i+1}/{total_accounts} 계정 처리 완료 ({(overall_progress_value*100):.1f}%)")
            
            time.sleep(0.3)  # UI 업데이트를 위한 대기
        
        # 결과 저장 (세션 상태)
        st.session_state['azure_vms'] = all_vms
        st.session_state['vm_last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        st.success(f"✅ 총 {len(all_vms)}개 Azure VM을 조회했습니다!")
        
        # 24시간 추이 데이터 수집
        if collect_trends and all_vms:
            st.markdown("---")
            st.subheader("📈 24시간 메트릭 추이 수집")
            
            # 전체 진행률 표시
            trend_progress = st.progress(0)
            trend_status = st.empty()
            
            all_trends = {}
            for i, account in enumerate(selected_configs):
                account_vms = [vm for vm in all_vms if vm['account_name'] == account['name']]
                if account_vms:
                    with st.expander(f"📈 [{i+1}/{len(selected_configs)}] {account['name']} 24시간 추이", expanded=True):
                        account_progress = st.progress(0)
                        account_status = st.empty()
                        
                        account_trends = get_vm_24h_metrics(account, account_vms, account_progress, account_status)
                        all_trends.update(account_trends)
                        
                        st.success(f"✅ {len(account_trends)}개 VM의 24시간 추이 데이터 수집 완료!")
                
                # 전체 진행률 업데이트
                trend_progress_value = (i + 1) / len(selected_configs)
                trend_progress.progress(trend_progress_value)
                trend_status.text(f"🔄 {i+1}/{len(selected_configs)} 계정 추이 데이터 수집 완료")
            
            # 24시간 추이 데이터 저장
            st.session_state['vm_trends'] = all_trends
            st.session_state['trends_last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            st.success(f"✅ 총 {len(all_trends)}개 VM의 24시간 추이 데이터 수집 완료!")
    
    # VM 결과 표시
    if 'azure_vms' in st.session_state:
        st.markdown("---")
        
        # 마지막 업데이트 시간
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("🖥️ Azure VM 모니터링 결과")
        with col2:
            st.caption(f"🕐 마지막 업데이트: {st.session_state.get('vm_last_update', 'N/A')}")
        
        vms_data = st.session_state['azure_vms']
        
        if vms_data:
            # DataFrame 생성
            df = pd.DataFrame(vms_data)
            
            # 주요 지표
            col1, col2, col3, col4 = st.columns(4)
            
            total_vms = len(df)
            running_vms = len(df[df['power_state'] == 'VM running'])
            stopped_vms = len(df[df['power_state'].str.contains('stopped|deallocated', case=False, na=False)])
            
            with col1:
                st.metric("총 VM", total_vms)
            with col2:
                st.metric("실행 중", running_vms)
            with col3:
                st.metric("중지됨", stopped_vms)
            with col4:
                st.metric("메트릭 수집", "Phase 2에서 구현 예정")
            
            st.markdown("---")
            
            # 차트
            col1, col2 = st.columns(2)
            
            with col1:
                # 계정별 VM 수
                account_counts = df.groupby('account_name').size().reset_index(name='count')
                fig1 = px.bar(
                    account_counts, 
                    x='account_name', 
                    y='count',
                    title='📊 계정별 Azure VM 수',
                    color='count',
                    color_continuous_scale='Blues'
                )
                fig1.update_layout(showlegend=False)
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # 상태별 VM 분포
                state_counts = df['power_state'].value_counts().reset_index()
                state_counts.columns = ['power_state', 'count']
                
                colors = {'VM running': '#28a745', 'VM stopped': '#dc3545', 'VM deallocated': '#6c757d'}
                fig2 = px.pie(
                    state_counts, 
                    values='count', 
                    names='power_state',
                    title='📈 VM 상태 분포',
                    color='power_state',
                    color_discrete_map=colors
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            st.markdown("---")
            
            # 상세 테이블
            st.subheader("📋 상세 Azure VM 목록")
            
            # 필터링 옵션
            col1, col2 = st.columns(2)
            with col1:
                state_filter = st.multiselect(
                    "상태 필터",
                    df['power_state'].unique(),
                    default=df['power_state'].unique()
                )
            with col2:
                account_filter = st.multiselect(
                    "계정 필터",
                    df['account_name'].unique(),
                    default=df['account_name'].unique()
                )
            
            # 필터 적용
            filtered_df = df[
                (df['power_state'].isin(state_filter)) & 
                (df['account_name'].isin(account_filter))
            ]
            
            # 상태별 색상 스타일링
            def highlight_vm_status(row):
                state = row['power_state']
                if 'running' in state.lower():
                    return [
                        'background-color: #d1f2eb; color: #0e6655; font-weight: bold; border-left: 4px solid #28a745;'
                    ] * len(row)
                elif 'stopped' in state.lower() or 'deallocated' in state.lower():
                    return [
                        'background-color: #fadbd8; color: #a93226; font-weight: bold; border-left: 4px solid #dc3545;'
                    ] * len(row)
                elif 'starting' in state.lower() or 'stopping' in state.lower():
                    return [
                        'background-color: #fef9e7; color: #7d6608; font-weight: bold; border-left: 4px solid #ffc107;'
                    ] * len(row)
                else:
                    return [
                        'background-color: #ebf3fd; color: #1f4e79; font-weight: bold; border-left: 4px solid #007bff;'
                    ] * len(row)
            
            # 테이블 표시 (메트릭 포함)
            if collect_metrics:
                display_columns = ['account_name', 'vm_name', 'resource_group', 'power_state', 'vm_size', 
                                 'cpu_usage', 'memory_usage', 'disk_usage', 'location', 'os_type']
            else:
                display_columns = ['account_name', 'vm_name', 'resource_group', 'power_state', 'vm_size', 
                                 'location', 'os_type', 'private_ip']
            
            styled_df = filtered_df[display_columns].style.apply(highlight_vm_status, axis=1)
            
            st.dataframe(
                styled_df,
                use_container_width=True,
                column_config={
                    "account_name": "계정명",
                    "vm_name": "VM명",
                    "resource_group": "리소스 그룹",
                    "power_state": "전원 상태",
                    "vm_size": "VM 크기",
                    "cpu_usage": "CPU 사용률",
                    "memory_usage": "메모리",
                    "disk_usage": "디스크 I/O",
                    "location": "위치",
                    "os_type": "OS 종류",
                    "private_ip": "프라이빗 IP"
                },
                height=400
            )
            
            # 24시간 추이 차트 표시
            if 'vm_trends' in st.session_state and st.session_state['vm_trends']:
                st.markdown("---")
                st.subheader("📈 24시간 VM 메트릭 추이")
                
                col1, col2 = st.columns([3, 1])
                with col2:
                    st.caption(f"🕐 추이 데이터 업데이트: {st.session_state.get('trends_last_update', 'N/A')}")
                
                trends_data = st.session_state['vm_trends']
                
                # VM 선택 드롭다운
                vm_names = list(trends_data.keys())
                if vm_names:
                    selected_vm = st.selectbox("🖥️ 추이를 볼 VM 선택", vm_names)
                    
                    if selected_vm and selected_vm in trends_data:
                        vm_trend = trends_data[selected_vm]
                        
                        # CPU 추이 차트
                        if vm_trend['cpu_trend']:
                            st.markdown("#### 📶 CPU 사용률 추이 (24시간)")
                            
                            cpu_df = pd.DataFrame(vm_trend['cpu_trend'])
                            cpu_df['timestamp'] = pd.to_datetime(cpu_df['timestamp'])
                            
                            # KST로 변환
                            KST = timezone(timedelta(hours=9))
                            cpu_df['timestamp_kst'] = cpu_df['timestamp'].dt.tz_convert(KST)
                            
                            fig_cpu = px.line(
                                cpu_df, 
                                x='timestamp_kst', 
                                y='value',
                                title=f"VM '{selected_vm}' CPU 사용률 (최근 24시간)",
                                labels={'value': 'CPU 사용률 (%)', 'timestamp_kst': '시간 (KST)'},
                                line_shape='spline'
                            )
                            fig_cpu.update_traces(line_color='#2E8B57', line_width=3)
                            fig_cpu.update_layout(
                                xaxis_title="시간 (KST)",
                                yaxis_title="CPU 사용률 (%)",
                                hovermode='x unified',
                                showlegend=False
                            )
                            st.plotly_chart(fig_cpu, use_container_width=True)
                        
                        # 디스크 I/O 추이 차트
                        if vm_trend['disk_trend']:
                            st.markdown("#### 💾 디스크 I/O 추이 (24시간)")
                            
                            disk_df = pd.DataFrame(vm_trend['disk_trend'])
                            disk_df['timestamp'] = pd.to_datetime(disk_df['timestamp'])
                            
                            # KST로 변환
                            disk_df['timestamp_kst'] = disk_df['timestamp'].dt.tz_convert(KST)
                            
                            fig_disk = px.line(
                                disk_df, 
                                x='timestamp_kst', 
                                y='value',
                                title=f"VM '{selected_vm}' 디스크 읽기 (최근 24시간)",
                                labels={'value': '디스크 읽기 (MB/h)', 'timestamp_kst': '시간 (KST)'},
                                line_shape='spline'
                            )
                            fig_disk.update_traces(line_color='#4169E1', line_width=3)
                            fig_disk.update_layout(
                                xaxis_title="시간 (KST)",
                                yaxis_title="디스크 읽기 (MB/h)",
                                hovermode='x unified',
                                showlegend=False
                            )
                            st.plotly_chart(fig_disk, use_container_width=True)
                        
                        # 요약 통계
                        if vm_trend['cpu_trend']:
                            cpu_values = [point['value'] for point in vm_trend['cpu_trend']]
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("평균 CPU", f"{sum(cpu_values)/len(cpu_values):.1f}%")
                            with col2:
                                st.metric("최대 CPU", f"{max(cpu_values):.1f}%")
                            with col3:
                                st.metric("최소 CPU", f"{min(cpu_values):.1f}%")
                else:
                    st.info("📊 24시간 추이 데이터가 없습니다. '추이 데이터 수집' 옵션을 체크하고 다시 조회해주세요.")
            
            # 데이터 다운로드
            st.markdown("---")
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 CSV 다운로드",
                data=csv,
                file_name=f"azure_vm_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        else:
            st.info("📊 조회된 Azure VM이 없습니다.")
    
    else:
        # 초기 화면
        st.info("👈 Azure 계정을 선택하고 'Azure VM 상태 조회' 버튼을 클릭하세요.")
        
        # 설정 파일 정보 표시
        if config and accounts:
            st.subheader("📋 설정된 Azure 계정 목록")
            account_df = pd.DataFrame([
                {
                    '계정명': acc['name'],
                    '설명': acc.get('description', ''),
                    '구독 ID': acc['subscription_id'][:8] + '...'  # 보안을 위해 일부만 표시
                }
                for acc in accounts
            ])
            st.dataframe(account_df, use_container_width=True)

def main():
    """메인 애플리케이션"""
    st.title("☁️ 클라우드 인프라 모니터링 대시보드")
    st.markdown("Azure 백업 및 VM 통합 모니터링")
    st.markdown("---")
    
    # 탭 생성
    tab1, tab2 = st.tabs(["💾 Azure 백업 모니터링", "🖥️ Azure VM 모니터링"])
    
    with tab1:
        display_azure_backup_monitoring()
    
    with tab2:
        display_vm_monitoring()

def display_azure_backup_monitoring():
    """Azure 백업 모니터링 화면"""
    
    # 설정 파일 로드
    config = load_accounts_config()
    if not config:
        st.stop()
    
    accounts = config.get('accounts', [])
    if not accounts:
        st.error("❌ 설정된 Azure 계정이 없습니다.")
        st.stop()
    
    # 계정 선택
    account_names = [acc['name'] for acc in accounts]
    selected_accounts = st.multiselect(
        "🏢 모니터링할 Azure 계정 선택",
        account_names,
        default=account_names,
        help="백업 상태를 확인할 계정을 선택하세요"
    )
    
    # 자동 새로고침 설정
    auto_refresh = st.checkbox("🔄 자동 새로고침 (30초)", value=False)
    if auto_refresh:
        time.sleep(30)
        st.rerun()
    
    # 오늘 백업만 표시 설정
    today_only = st.checkbox("📅 오늘 백업만 표시", value=True, help="체크하면 오늘 실행된 백업 작업만 표시됩니다")
    
    # 실행 버튼
    if st.button("🚀 백업 상태 조회", type="primary"):
        if not selected_accounts:
            st.warning("⚠️ 최소 하나의 계정을 선택해주세요.")
            return
        
        # 선택된 계정 필터링
        selected_account_configs = [acc for acc in accounts if acc['name'] in selected_accounts]
        
        # 개선된 진행상황 표시
        st.subheader("🔄 백업 모니터링 진행 중...")
        
        # 전체 진행률 표시
        overall_progress = st.progress(0)
        overall_status = st.empty()
        
        # 상세 정보 컨테이너
        with st.container():
            st.markdown("### 📊 실시간 진행 상황")
            
            all_jobs = []
            total_accounts = len(selected_account_configs)
            
            for i, account in enumerate(selected_account_configs):
                # 계정별 섹션
                with st.expander(f"🏢 [{i+1}/{total_accounts}] {account['name']}", expanded=True):
                    
                    # 개별 계정 진행상황
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # 계정 정보 표시
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**구독 ID:** {account['subscription_id'][:8]}...")
                    with col2:
                        st.write(f"**테넌트 ID:** {account['tenant_id'][:8]}...")
                    
                    # 작업 시작 시간 기록
                    start_time = time.time()
                    
                    jobs = get_backup_jobs(account, progress_bar, status_text)
                    all_jobs.extend(jobs)
                    
                    # 작업 완료 시간 계산
                    elapsed_time = time.time() - start_time
                    
                    # 결과 요약 표시
                    if jobs:
                        st.success(f"✅ {len(jobs)}개 백업 작업 조회 완료 ({elapsed_time:.1f}초 소요)")
                    else:
                        st.info(f"ℹ️ 백업 작업 없음 ({elapsed_time:.1f}초 소요)")
                
                # 전체 진행률 업데이트
                overall_progress_value = (i + 1) / total_accounts
                overall_progress.progress(overall_progress_value)
                overall_status.text(f"🔄 {i+1}/{total_accounts} 계정 처리 완료 ({(overall_progress_value*100):.1f}%)")
                
                time.sleep(0.3)  # UI 업데이트를 위한 대기
        
        # 결과 저장 (세션 상태)
        st.session_state['backup_jobs'] = all_jobs
        st.session_state['today_only'] = today_only
        st.session_state['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 오늘 백업 필터링을 위한 카운트
        if today_only:
            today = datetime.now().date()
            today_jobs = [job for job in all_jobs if job.get('start_time_raw') and 
                         (isinstance(job['start_time_raw'], datetime) and job['start_time_raw'].date() == today)]
            st.success(f"✅ 총 {len(all_jobs)}개 백업 작업 조회 완료! (오늘 실행: {len(today_jobs)}개)")
        else:
            st.success(f"✅ 총 {len(all_jobs)}개 백업 작업을 조회했습니다!")
    
    # 결과 표시
    if 'backup_jobs' in st.session_state:
        st.markdown("---")
        
        # 마지막 업데이트 시간
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("📊 백업 모니터링 결과")
        with col2:
            st.caption(f"🕐 마지막 업데이트: {st.session_state.get('last_update', 'N/A')}")
        
        jobs_data = st.session_state['backup_jobs']
        
        # 결과 페이지에서도 오늘 백업만 표시 옵션 제공
        col_filter1, col_filter2 = st.columns([2, 1])
        with col_filter2:
            show_today_only = st.checkbox("📅 오늘 백업만 표시", 
                                        value=st.session_state.get('today_only', True),
                                        key="result_today_filter",
                                        help="체크하면 오늘 실행된 백업만 표시됩니다")
        
        if jobs_data:
            # DataFrame 생성
            df = pd.DataFrame(jobs_data)
            
            # start_time_raw가 문자열인 경우 datetime으로 변환
            if 'start_time_raw' in df.columns:
                df['start_time_raw'] = pd.to_datetime(df['start_time_raw'], errors='coerce')
            
            # 오늘 백업만 표시 필터링
            if show_today_only and 'start_time_raw' in df.columns:
                today = datetime.now().date()
                df = df[df['start_time_raw'].dt.date == today]
                
                # 필터링 후 결과 안내
                if len(df) == 0:
                    st.info("📅 오늘 실행된 백업 작업이 없습니다.")
                    st.info("💡 전체 백업 내역을 보려면 사이드바에서 '오늘 백업만 표시' 체크를 해제하세요.")
                else:
                    st.info(f"📅 오늘({today.strftime('%Y-%m-%d')}) 실행된 백업 작업: {len(df)}개")
            
            # 주요 지표
            display_metrics(df)
            
            st.markdown("---")
            
            # 차트
            create_summary_charts(df)
            
            st.markdown("---")
            
            # 상세 테이블
            st.subheader("📋 상세 백업 작업 목록")
            
            # 필터링 옵션
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.multiselect(
                    "상태 필터",
                    df['status'].unique(),
                    default=df['status'].unique()
                )
            with col2:
                account_filter = st.multiselect(
                    "계정 필터",
                    df['account_name'].unique(),
                    default=df['account_name'].unique()
                )
            
            # 필터 적용
            filtered_df = df[
                (df['status'].isin(status_filter)) & 
                (df['account_name'].isin(account_filter))
            ]
            
            # 개선된 상태별 색상 및 스타일링
            def highlight_status(row):
                status = row['status']
                if status == 'Completed':
                    return [
                        'background-color: #d1f2eb; color: #0e6655; font-weight: bold; border-left: 4px solid #28a745;'
                    ] * len(row)
                elif status in ['Failed', 'Cancelled']:
                    return [
                        'background-color: #fadbd8; color: #a93226; font-weight: bold; border-left: 4px solid #dc3545;'
                    ] * len(row)
                elif status in ['InProgress', 'Running']:
                    return [
                        'background-color: #fef9e7; color: #7d6608; font-weight: bold; border-left: 4px solid #ffc107;'
                    ] * len(row)
                else:
                    return [
                        'background-color: #ebf3fd; color: #1f4e79; font-weight: bold; border-left: 4px solid #007bff;'
                    ] * len(row)
            
            # 테이블 표시 - 컬럼 확장
            display_columns = ['account_name', 'vault_name', 'status', 'start_time', 'end_time', 'duration', 'resource_group']
            
            # 데이터 정렬 (시작 시간 기준 내림차순)
            filtered_df_sorted = filtered_df.sort_values('start_time', ascending=False, na_position='last')
            
            styled_df = filtered_df_sorted[display_columns].style.apply(highlight_status, axis=1)
            
            st.dataframe(
                styled_df,
                use_container_width=True,
                column_config={
                    "account_name": "계정명",
                    "vault_name": "Vault명", 
                    "status": "상태",
                    "start_time": "시작 시간",
                    "end_time": "종료 시간",
                    "duration": "소요 시간", 
                    "resource_group": "리소스 그룹"
                },
                height=400
            )
            
            # 실패한 작업 하이라이트
            failed_jobs = filtered_df_sorted[filtered_df_sorted['status'].isin(['Failed', 'Cancelled'])]
            if not failed_jobs.empty:
                st.subheader("🚨 실패한 백업 작업")
                failed_styled_df = failed_jobs[display_columns].style.apply(highlight_status, axis=1)
                st.dataframe(
                    failed_styled_df,
                    use_container_width=True,
                    column_config={
                        "account_name": "계정명",
                        "vault_name": "Vault명",
                        "status": "상태",
                        "start_time": "시작 시간",
                        "end_time": "종료 시간",
                        "duration": "소요 시간",
                        "resource_group": "리소스 그룹"
                    },
                    height=200
                )
            
            # 데이터 다운로드
            st.markdown("---")
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 CSV 다운로드",
                data=csv,
                file_name=f"backup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        else:
            st.info("📊 조회된 백업 작업이 없습니다.")
    
    else:
        # 초기 화면
        st.info("👈 사이드바에서 계정을 선택하고 '백업 상태 조회' 버튼을 클릭하세요.")
        
        # 설정 파일 정보 표시
        if config and accounts:
            st.subheader("📋 설정된 계정 목록")
            account_df = pd.DataFrame([
                {
                    '계정명': acc['name'],
                    '설명': acc.get('description', ''),
                    '구독 ID': acc['subscription_id'][:8] + '...'  # 보안을 위해 일부만 표시
                }
                for acc in accounts
            ])
            st.dataframe(account_df, use_container_width=True)

if __name__ == "__main__":
    main()