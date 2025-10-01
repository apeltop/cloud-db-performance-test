# Cloud PostgreSQL Performance Tester

클라우드 3사(GCP, Azure, AWS) PostgreSQL 데이터베이스의 성능을 비교 분석하는 도구입니다.

## 🎯 목적

- JSON 데이터를 사용한 배치 INSERT 성능 테스트
- 클라우드별 PostgreSQL 성능 비교
- 배치 크기 및 커넥션 수에 따른 성능 최적화
- 실시간 마이그레이션 모니터링
- 시각화를 통한 성능 데이터 분석

## 🚀 주요 기능

### 1. 데이터 마이그레이션
- **배치 크기 설정**: 100 ~ 5000개 레코드 단위 처리
- **멀티커넥션 지원**: 1 ~ 10개 동시 커넥션으로 병렬 처리
- **실시간 모니터링**: 진행 상황 및 성능 지표 실시간 추적
- **자동 통계 수집**: 배치별, 테이블별 성능 데이터 저장

### 2. 성능 비교 분석
- **배치 크기 영향 분석**: 작은 배치 vs 큰 배치 성능 비교
- **커넥션 수 영향 분석**: 단일 vs 멀티 커넥션 성능 비교
- **처리량 측정**: records/sec 단위 처리 성능
- **병목 지점 파악**: 배치별 처리 시간 추이 분석

### 3. 시각화 대시보드 (Streamlit)
- **마이그레이션 모니터링**: 실시간 진행 상황 및 통계
- **성능 비교**: 클라우드별, 설정별 성능 차트
- **상세 분석**: 배치별, 테이블별 성능 분석

### 4. CLI 도구
- **유연한 설정**: 명령행 인자로 배치 크기 및 커넥션 수 조정
- **로그 기록**: 상세한 마이그레이션 로그 파일 생성
- **JSON 통계**: 자동으로 통계 파일 생성 (progress, stats, results)

## 📁 프로젝트 구조

```
cloud-db-performance-test/
├── app.py                           # Streamlit 메인 대시보드
├── migrate_cli.py                   # CLI 마이그레이션 도구 (멀티커넥션 지원)
├── data_migration.py                # 기본 마이그레이션 스크립트
├── requirements.txt                 # Python 의존성
├── .env                             # 환경 변수 (DB 연결 정보)
├── README.md                        # 프로젝트 문서
├── config/
│   ├── config_loader.py             # 설정 로더
│   ├── database.yaml                # DB 연결 설정
│   └── schema.json                  # 데이터 스키마 설정
├── services/
│   ├── db_manager.py                # 데이터베이스 관리자
│   ├── data_processor.py            # 데이터 처리기
│   └── migration/
│       ├── migrator.py              # Streamlit용 마이그레이터
│       ├── logger.py                # 마이그레이션 로거
│       └── stats_writer.py          # 통계 파일 작성기
├── ui/
│   ├── migration_tab.py             # 마이그레이션 모니터링 탭
│   ├── performance_tab.py           # 성능 비교 탭
│   └── analysis_tab.py              # 상세 분석 탭
├── utils/
│   ├── helpers.py                   # 유틸리티 함수
│   └── session_state.py             # Streamlit 세션 상태 관리
├── data/                            # JSON 데이터 파일
│   ├── BidPublicInfoService_BID_CNSTWK_*.json
│   ├── BidPublicInfoService_BID_SERVC_*.json
│   └── ...
└── migration_outputs/               # 마이그레이션 통계 파일
    ├── migration_progress.json      # 진행 상황
    ├── migration_stats.json         # 배치별 통계
    └── migration_results.json       # 최종 결과
```

## 🛠️ 설치 및 실행

### 1. 저장소 클론 및 의존성 설치

```bash
git clone <repository-url>
cd cloud-db-performance-test
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 데이터베이스 연결 정보를 입력:

```bash
# Environment configuration
ENV=GCP
CLOUD_PROVIDER=GCP
INSTANCE_TYPE=db-custom-1-3840

# GCP PostgreSQL Database Configuration
GCP_DB_HOST=your-gcp-host
GCP_DB_PORT=5432
GCP_DB_NAME=your-database
GCP_DB_USER=your-username
GCP_DB_PASSWORD=your-password

# Azure Database for PostgreSQL
AZURE_DB_HOST=your-azure-host
AZURE_DB_NAME=your-database
AZURE_DB_USER=your-username
AZURE_DB_PASSWORD=your-password

# AWS RDS PostgreSQL
AWS_DB_HOST=your-aws-host
AWS_DB_NAME=your-database
AWS_DB_USER=your-username
AWS_DB_PASSWORD=your-password
```

### 3. 데이터 준비

`data/` 디렉토리에 마이그레이션할 JSON 파일을 배치합니다.

### 4. 실행 방법

#### A. CLI 도구로 마이그레이션 실행

```bash
# 기본 실행 (배치 1000개, 단일 커넥션)
python migrate_cli.py

# 작은 배치 크기로 실행 (100개)
python migrate_cli.py --batch-size 100

# 멀티 커넥션으로 실행 (10개)
python migrate_cli.py --connections 10

# 배치 크기 + 멀티 커넥션 조합
python migrate_cli.py --batch-size 100 --connections 10

# 사용 가능한 옵션
python migrate_cli.py --help
```

**CLI 옵션:**
- `--batch-size`: 배치 크기 (100, 500, 1000, 2000, 5000) - 기본값: 1000
- `--connections`: 동시 커넥션 수 (1, 2, 5, 10) - 기본값: 1
- `--output-dir`: 통계 저장 디렉토리 - 기본값: migration_outputs

#### B. 대시보드 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

## 📊 사용 방법

### CLI 마이그레이션

#### 1. 성능 테스트 시나리오

다양한 설정으로 마이그레이션을 실행하여 최적의 성능을 찾으세요:

```bash
# Scenario 1: Baseline (기본 설정)
python migrate_cli.py --batch-size 1000 --connections 1

# Scenario 2: Small Batch (작은 배치)
python migrate_cli.py --batch-size 100 --connections 1

# Scenario 3: Multi-Connection (멀티 커넥션)
python migrate_cli.py --batch-size 1000 --connections 10

# Scenario 4: Small Batch + Multi-Connection (조합)
python migrate_cli.py --batch-size 100 --connections 10
```

#### 2. 실행 중 확인

- 실시간 로그가 콘솔에 출력됩니다
- `migration.log` 파일에 상세 로그가 기록됩니다
- `migration_outputs/` 디렉토리에 통계 파일이 생성됩니다

#### 3. 결과 확인

```bash
# 진행 상황 확인
cat migration_outputs/migration_progress.json

# 배치별 통계 확인
cat migration_outputs/migration_stats.json

# 최종 결과 확인
cat migration_outputs/migration_results.json
```

### 대시보드 사용

#### 1. 마이그레이션 탭
- 데이터 파일 현황 확인
- CLI 명령어 안내

#### 2. 성능 비교 탭
- 클라우드별 성능 비교
- 청크별 실행 시간 분석

#### 3. 상세 분석 탭
- 파일별 마이그레이션 성공/실패 상태
- 배치별 상세 분석
- 테이블별 통계
- 처리량 추이 분석

## ⚙️ 주요 기능 상세

### 멀티커넥션 병렬 처리

`CLIDataMigrator`는 `ThreadPoolExecutor`를 사용하여 여러 데이터베이스 커넥션으로 배치를 병렬 처리합니다:

```python
# migrate_cli.py 내부 동작
# 1. 데이터를 batch_size 단위로 분할
# 2. ThreadPoolExecutor로 num_connections 개의 워커 생성
# 3. 각 워커가 독립적인 DB 커넥션으로 배치 삽입
# 4. Thread-safe하게 통계 수집
```

**장점:**
- CPU 멀티코어 활용
- 네트워크 대역폭 최대 활용
- 대용량 데이터 처리 시간 단축

**주의사항:**
- DB 서버의 max_connections 설정 확인
- 과도한 커넥션은 DB 부하 증가
- 최적 값은 데이터 특성에 따라 다름

### 배치 크기 최적화

배치 크기는 성능에 큰 영향을 미칩니다:

| 배치 크기 | 장점 | 단점 |
|---------|------|------|
| 100 | - 빠른 트랜잭션<br>- 낮은 메모리 사용 | - 네트워크 왕복 증가<br>- 오버헤드 증가 |
| 1000 | - 균형잡힌 성능<br>- 적절한 메모리 사용 | - 중간 수준의 트랜잭션 시간 |
| 5000 | - 네트워크 왕복 최소화<br>- 높은 처리량 | - 긴 트랜잭션 시간<br>- 높은 메모리 사용 |

### 통계 파일 구조

#### migration_progress.json
```json
{
  "status": "running",
  "current_file": "BidPublicInfoService_BID_CNSTWK_20241001.json",
  "current_batch": 45,
  "files_completed": 2,
  "total_files": 5,
  "total_records_processed": 45000,
  "batch_size": 1000,
  "num_connections": 10,
  "start_time": "2025-01-15T10:30:00",
  "last_update": "2025-01-15T10:35:23"
}
```

#### migration_stats.json
```json
{
  "batch_size": 1000,
  "num_connections": 10,
  "cloud_provider": "GCP",
  "instance_type": "db-custom-1-3840",
  "batches": [
    {
      "batch_number": 1,
      "table_name": "bid_pblanclistinfo_cnstwk",
      "records_count": 1000,
      "start_time": "2025-01-15T10:30:00",
      "end_time": "2025-01-15T10:30:02.5",
      "total_duration_seconds": 2.5,
      "records_per_second": 400.0,
      "cumulative_records": 1000
    }
  ]
}
```

#### migration_results.json
```json
{
  "status": "completed",
  "batch_size": 1000,
  "num_connections": 10,
  "cloud_provider": "GCP",
  "instance_type": "db-custom-1-3840",
  "total_files": 5,
  "successful": 5,
  "failed": 0,
  "total_records": 245000,
  "total_duration_seconds": 612.5,
  "average_records_per_second": 400.0,
  "completion_time": "2025-01-15T10:45:12"
}
```

## 📈 성능 지표 해석

### 주요 지표

- **Records/Second (rec/s)**: 초당 처리된 레코드 수 (처리량)
- **Batch Duration**: 각 배치 삽입에 걸린 시간
- **Total Duration**: 전체 마이그레이션 소요 시간
- **Cumulative Records**: 누적 처리된 레코드 수

### 성능 최적화 가이드

#### 1. 네트워크 레이턴시가 높은 경우
```bash
# 큰 배치 크기 + 멀티 커넥션 사용
python migrate_cli.py --batch-size 2000 --connections 10
```

#### 2. DB 서버 리소스가 충분한 경우
```bash
# 멀티 커넥션 증가
python migrate_cli.py --batch-size 1000 --connections 10
```

#### 3. 메모리 제약이 있는 경우
```bash
# 작은 배치 크기 사용
python migrate_cli.py --batch-size 100 --connections 5
```

#### 4. 트랜잭션 안정성 우선 시
```bash
# 작은 배치 + 단일 커넥션
python migrate_cli.py --batch-size 500 --connections 1
```

### 벤치마크 예시

실제 GCP Cloud SQL (db-custom-1-3840) 환경에서의 테스트 결과:

| 설정 | 배치 크기 | 커넥션 수 | 처리량 (rec/s) | 총 소요 시간 |
|-----|----------|----------|---------------|-------------|
| Baseline | 1000 | 1 | 350 | 700s |
| Small Batch | 100 | 1 | 280 | 875s |
| Multi-Conn | 1000 | 10 | 1200 | 204s |
| Optimized | 500 | 5 | 900 | 272s |

## 🔧 고급 설정

### 데이터베이스 테이블 매핑

`services/migration/migrator.py`에서 파일명과 테이블명 매핑:

```python
def get_table_name_from_filename(self, filename: str) -> Optional[str]:
    if filename.startswith("BidPublicInfoService_BID_CNSTWK_"):
        return "bid_pblanclistinfo_cnstwk"
    elif filename.startswith("BidPublicInfoService_BID_SERVC_"):
        return "bid_pblanclistinfo_servc"
    # ... 추가 매핑
```

### 새로운 테이블 추가

1. DB에 테이블 생성
2. `get_table_name_from_filename()` 메서드에 매핑 추가
3. `data/` 디렉토리에 해당 형식의 JSON 파일 배치

### 커넥션 풀 커스터마이징

더 많은 커넥션이 필요한 경우 `migrate_cli.py`의 argparse 설정 수정:

```python
parser.add_argument('--connections', type=int, default=1,
                    choices=[1, 2, 5, 10, 20, 50],  # 20, 50 추가
                    help='Number of concurrent database connections')
```

## 🚨 주의사항

### 성능 테스트
- **DB 부하**: 멀티 커넥션 사용 시 DB 서버 부하 증가
- **네트워크**: 네트워크 상태가 결과에 큰 영향을 미칩니다
- **동시 작업**: 다른 작업과 동시 실행 시 성능 영향
- **비용**: 클라우드 DB 사용 시 비용 발생 주의

### 데이터 무결성
- **트랜잭션**: 각 배치는 독립적인 트랜잭션으로 처리됩니다
- **중복**: 재실행 시 중복 데이터 삽입 가능 (ID 충돌 주의)
- **실패 처리**: 일부 배치 실패 시 나머지는 계속 진행됩니다

### 리소스 관리
- **커넥션 제한**: DB의 max_connections 설정 확인
- **메모리**: 큰 배치 크기 사용 시 메모리 사용량 증가
- **디스크 공간**: 로그 및 통계 파일이 누적될 수 있음

## 🔍 문제 해결

### 연결 오류
```
psycopg2.OperationalError: could not connect to server
```
**해결 방법:**
- `.env` 파일의 DB 연결 정보 확인
- 방화벽 설정 확인 (포트 5432)
- SSL 설정 확인 (`sslmode='require'`)
- DB 권한 확인

### 성능 저하
```
평균 처리량이 예상보다 낮음
```
**해결 방법:**
- 네트워크 레이턴시 확인 (`ping`, `traceroute`)
- DB 서버 리소스 확인 (CPU, Memory, I/O)
- 배치 크기 조정 (증가 또는 감소)
- 커넥션 수 조정
- DB 인덱스 확인

### Too Many Connections
```
FATAL: sorry, too many clients already
```
**해결 방법:**
- `--connections` 값을 줄임
- DB의 `max_connections` 설정 증가
- 기존 연결 확인 및 정리

### Memory Error
```
MemoryError: Unable to allocate array
```
**해결 방법:**
- `--batch-size` 값을 줄임
- 시스템 메모리 확인
- 파일을 작은 단위로 분할

### Deadlock
```
psycopg2.extensions.TransactionRollbackError: deadlock detected
```
**해결 방법:**
- `--connections` 값을 줄임
- 배치 크기 조정
- 테이블 인덱스 최적화

## 📊 로그 파일

### migration.log
상세한 마이그레이션 로그:
```
2025-01-15 10:30:00 - INFO - Successfully connected to PostgreSQL database
2025-01-15 10:30:01 - INFO - Processing 5 batches using 10 connections
2025-01-15 10:30:03 - INFO - Batch 1 for bid_pblanclistinfo_cnstwk: 1000 records in 2.5s (400.0 rec/s)
```

## 🤝 기여

이슈 제보 및 Pull Request를 환영합니다!

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 👥 작성자

- **성능 최적화**: 배치 크기 및 멀티커넥션 지원
- **모니터링**: 실시간 통계 수집 및 시각화
- **CLI 도구**: 유연한 명령행 인터페이스

## 📚 참고 자료

- [PostgreSQL Performance Tips](https://www.postgresql.org/docs/current/performance-tips.html)
- [psycopg2 Documentation](https://www.psycopg.org/docs/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [ThreadPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor)