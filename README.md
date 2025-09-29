# Cloud PostgreSQL Performance Tester

클라우드 3사(GCP, Azure, AWS) PostgreSQL 데이터베이스의 성능을 비교 분석하는 도구입니다.

## 🎯 목적

- JSON 데이터를 사용한 배치 INSERT 성능 테스트
- 클라우드별 PostgreSQL 성능 비교
- 실행 시간 측정 및 통계 분석
- 시각화를 통한 성능 데이터 분석

## 🚀 주요 기능

### 1. 데이터 처리
- JSON 파일 업로드 및 파싱
- 설정 가능한 청크 크기 (기본값: 10개)
- 배치 INSERT 최적화

### 2. 성능 측정
- 클라우드별 동시 테스트
- 청크별 실행 시간 측정
- 성공률 및 에러 추적
- 처리량(records/sec) 계산

### 3. 시각화 대시보드
- 실시간 성능 비교 차트
- 클라우드별 상세 통계
- 실행 시간 분포 분석
- 결과 내보내기 (CSV, JSON)

### 4. 설정 관리
- 환경변수 기반 DB 연결 설정
- JSON 스키마 설정 파일
- Mock 모드 지원 (실제 DB 없이 테스트)

## 📁 프로젝트 구조

```
jodal-insert-test/
├── app.py                      # Streamlit 메인 애플리케이션
├── requirements.txt            # Python 의존성
├── README.md                   # 프로젝트 문서
├── config/
│   ├── config_loader.py        # 설정 로더
│   ├── database.yaml           # DB 연결 설정
│   └── schema.json             # 데이터 스키마 설정
├── services/
│   ├── db_manager.py           # 데이터베이스 관리자
│   └── data_processor.py       # 데이터 처리기
├── utils/
│   └── helpers.py              # 유틸리티 함수
├── data/
│   └── sample_data.json        # 샘플 데이터
└── results/                    # 테스트 결과 저장
```

## 🛠️ 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정 (선택사항)

실제 클라우드 DB 연결 시:

```bash
# GCP
export GCP_DB_HOST="your-gcp-host"
export GCP_DB_NAME="your-database"
export GCP_DB_USER="your-username"
export GCP_DB_PASSWORD="your-password"

# Azure
export AZURE_DB_HOST="your-azure-host"
export AZURE_DB_NAME="your-database"
export AZURE_DB_USER="your-username"
export AZURE_DB_PASSWORD="your-password"

# AWS
export AWS_DB_HOST="your-aws-host"
export AWS_DB_NAME="your-database"
export AWS_DB_USER="your-username"
export AWS_DB_PASSWORD="your-password"
```

### 3. 애플리케이션 실행

```bash
streamlit run app.py
```

## 📊 사용 방법

### 1. 데이터 업로드
- **JSON 파일 업로드**: 테스트할 JSON 데이터 파일 선택
- **샘플 데이터 사용**: 미리 준비된 20개 레코드 사용

### 2. 테스트 설정
- **청크 크기**: 한 번에 처리할 레코드 수 (5-50개)
- **클라우드 선택**: 테스트할 클라우드 서비스 선택
- **Mock 모드**: 실제 DB 없이 시뮬레이션 테스트

### 3. 결과 분석
- **성능 비교**: 클라우드별 평균 실행 시간 및 처리량 비교
- **상세 분석**: 청크별 실행 시간, 분포 분석
- **통계 테이블**: 성공률, 최소/최대 시간 등 상세 통계

### 4. 결과 내보내기
- **CSV**: 상세 실행 결과 데이터
- **JSON**: 성능 요약 통계

## ⚙️ 설정 파일

### database.yaml
```yaml
clouds:
  gcp:
    name: "Google Cloud SQL"
    host: "${GCP_DB_HOST:-localhost}"
    # ... 기타 설정
  azure:
    # ... Azure 설정
  aws:
    # ... AWS 설정

mock_mode:
  enabled: true
  simulate_latency: true
  latency_ranges:
    gcp: [0.05, 0.15]  # 50-150ms
    azure: [0.08, 0.18]  # 80-180ms
    aws: [0.06, 0.16]   # 60-160ms
```

### schema.json
```json
{
  "table_name": "test_data",
  "fields": {
    "id": {"type": "SERIAL", "primary_key": true},
    "user_id": {"type": "INTEGER", "nullable": false},
    "name": {"type": "VARCHAR(100)", "nullable": false},
    "metadata": {"type": "JSONB", "nullable": true},
    // ... 기타 필드
  }
}
```

## 🔧 커스터마이징

### 새로운 데이터 스키마 추가

1. `config/schema.json` 수정
2. `data/` 디렉토리에 새로운 JSON 데이터 파일 추가
3. 애플리케이션 재시작

### 새로운 클라우드 프로바이더 추가

1. `config/database.yaml`에 새 클라우드 설정 추가
2. `services/db_manager.py`에서 연결 로직 확장
3. UI에서 새 클라우드 옵션 추가

## 📈 성능 지표

- **실행 시간**: 각 청크 INSERT 작업 소요 시간
- **처리량**: 초당 처리 레코드 수 (records/sec)
- **성공률**: 전체 작업 대비 성공한 작업 비율
- **지연시간 분포**: P50, P95, P99 백분위수

## 🚨 주의사항

- Mock 모드는 실제 DB 성능과 다를 수 있습니다
- 실제 클라우드 DB 사용 시 비용이 발생할 수 있습니다
- 대용량 데이터 테스트 시 청크 크기를 적절히 조정하세요
- 네트워크 상태가 결과에 영향을 줄 수 있습니다

## 🔍 문제 해결

### 연결 오류
- 환경 변수 설정 확인
- 네트워크 방화벽 설정 확인
- DB 권한 확인

### 성능 이상
- Mock 모드 비활성화 후 재테스트
- 청크 크기 조정
- 네트워크 상태 확인

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.