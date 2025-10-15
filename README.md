# 📊 주파수 영역 자산 분석 시스템

자산의 변동을 시간 스케일별로 분해하여 **어떤 시간대에 변동이 큰지**, **위기 때 상관관계가 어떻게 변하는지**, **진짜 리스크가 어디서 오는지**를 파악하는 고급 포트폴리오 분석 도구입니다.

## 🎯 주요 기능

### 1. 주파수 대역별 변동성 분해
자산의 변동성을 4개 시간 스케일로 분해:
- **단기 (5일~3개월)**: 시장 노이즈
- **중기 (3개월~1년)**: 계절성
- **경기순환 (1~5년)**: 경기 사이클
- **장기추세 (5년+)**: 구조적 변화

### 2. Risk-Return 분석
- 자산별 기대수익률, 변동성, 샤프지수
- 인터랙티브 산점도로 위험 대비 수익률 시각화
- 핵심 지표 카드 형식 표시

### 3. 상관관계 분석
- 자산 간 상관계수 히트맵
- 주파수 대역별 상관계수 분석
- 포트폴리오 분산 효과 인사이트

### 4. 다양한 시각화 옵션
- 누적 막대 차트
- 그룹 막대 차트
- 100% 누적 비율 차트

## 🚀 빠른 시작

### 온라인 사용 (권장)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](YOUR_STREAMLIT_URL_HERE)

### 로컬 실행

1. 저장소 클론
```bash
git clone https://github.com/YOUR_USERNAME/freq-analysis-app.git
cd freq-analysis-app
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 패키지 설치
```bash
pip install -r requirements.txt
```

4. 앱 실행
```bash
streamlit run app.py
```

## 📁 데이터 형식

CSV 또는 Excel 파일을 준비하세요:
- **인덱스**: 날짜 (YYYY-MM-DD)
- **컬럼**: 자산명
- **값**: 일별 수익률 (소수점 형식)
- **기간**: 최소 3년, 권장 5년 이상

### 예시
```csv
날짜,주식,채권,금
2019-01-01,0.01,0.002,0.005
2019-01-02,-0.005,0.001,-0.003
2019-01-03,0.008,0.0015,0.002
...
```

## 🛠️ 기술 스택

- **Frontend**: Streamlit
- **Data Processing**: Pandas, NumPy
- **Analysis**: SciPy (FFT, Signal Processing)
- **Visualization**: Plotly, Matplotlib
- **Methodology**: Ortec Finance Zero-Phase Filter 방법론

## 📊 분석 방법론

이 도구는 **Frequency Domain Analysis**를 사용하여:

1. **Power Spectral Density (PSD)**: 주파수별 변동성 크기 측정
2. **Zero-Phase Butterworth Filter**: 시간 지연 없이 주파수 대역 분리
3. **Cross-Spectral Density**: 주파수별 상관관계 계산

### 이론적 배경
- Ortec Finance의 주파수 영역 자산 배분 방법론
- Fourier Transform을 이용한 시계열 분해
- 나이퀴스트 정리를 고려한 주파수 대역 설정

## 💡 사용 사례

### 포트폴리오 관리
- 시간대별 리스크 집중도 파악
- 분산 효과 극대화를 위한 자산 선택
- 경기 사이클에 따른 자산 배분

### 리스크 관리
- 단기 노이즈 vs 구조적 리스크 구분
- 위기 시 상관관계 변화 모니터링
- 주파수 대역별 헤징 전략

## 📄 라이선스

MIT License

## 🤝 기여

이슈와 PR을 환영합니다!

## 📧 문의

질문이나 제안사항이 있으시면 이슈를 열어주세요.

---

**Powered by Streamlit** | **Based on Ortec Finance Methodology**
