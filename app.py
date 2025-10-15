"""
주파수 영역 자산 분석 시스템 - Streamlit UI
"""

import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import plotly.graph_objects as go
import plotly.express as px

from freq_domain_asset_analysis import FrequencyDomainAnalyzer, setup_korean_font

# 한글 폰트 설정
setup_korean_font()

# 페이지 설정
st.set_page_config(
    page_title="주파수 영역 자산 분석 시스템",
    page_icon="📊",
    layout="wide"
)

# 제목
st.title("📊 주파수 영역 자산 분석 시스템")
st.markdown("""
자산의 변동을 시간 스케일별로 분해하여 **어떤 시간대에 변동이 큰지**, **위기 때 상관관계가 어떻게 변하는지**,
**진짜 리스크가 어디서 오는지**를 파악하는 고급 포트폴리오 분석 도구입니다.
""")
st.divider()

# 세션 상태 초기화
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'returns_df' not in st.session_state:
    st.session_state.returns_df = None

# 사이드바 - 파일 업로드
with st.sidebar:
    st.header("📁 데이터 업로드")
    uploaded_file = st.file_uploader(
        "CSV 또는 Excel 파일을 업로드하세요",
        type=['csv', 'xlsx', 'xls'],
        help="날짜를 인덱스로, 자산 수익률을 컬럼으로 하는 파일을 업로드하세요"
    )

    st.divider()

    st.markdown("""
    ### 📋 데이터 형식
    - **인덱스**: 날짜 (YYYY-MM-DD)
    - **컬럼**: 자산명
    - **값**: 수익률 (일별 수익률 권장)
    - **기간**: 최소 3년, 권장 5년 이상

    ### 예시
    ```
    날짜        주식    채권    금
    2020-01-01  0.01   0.002   0.005
    2020-01-02 -0.005  0.001  -0.003
    ...
    ```

    ---

    ### 💡 주파수 분석이란?
    자산의 변동을 여러 시간 스케일로 분해하여:
    - 단기 (5일~3개월): 노이즈
    - 중기 (3개월~1년): 계절성
    - 경기순환 (1~5년): 경기 사이클
    - 장기추세 (5년+): 구조적 변화

    각 시간대별 리스크와 상관관계를 파악합니다.
    """)

# 메인 영역
if uploaded_file is not None or st.session_state.returns_df is not None:
    try:
        # 파일 읽기 또는 세션 데이터 사용
        if uploaded_file is not None:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, index_col=0, parse_dates=True)
            else:
                df = pd.read_excel(uploaded_file, index_col=0, parse_dates=True)
            st.session_state.returns_df = df
        else:
            df = st.session_state.returns_df

        # 데이터 미리보기
        st.header("📄 데이터 미리보기")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("데이터 기간", f"{len(df)}일")
        with col2:
            st.metric("자산 개수", f"{len(df.columns)}개")
        with col3:
            st.metric("시작일 ~ 종료일", f"{df.index[0].date()} ~ {df.index[-1].date()}")

        st.dataframe(df.head(10), width='stretch')

        # 기본 통계
        with st.expander("📊 기본 통계량 보기"):
            st.dataframe(df.describe(), width='stretch')

        st.divider()

        # 분석 시작 버튼
        st.header("🚀 분석 실행")

        col1, col2 = st.columns([1, 3])
        with col1:
            analyze_button = st.button(
                "🔍 분석 시작",
                type="primary",
                width="stretch"  # Note: Streamlit buttons don't use width parameter
            )

        # 분석 실행
        if analyze_button:
            with st.spinner('분석 중... 잠시만 기다려주세요 ⏳'):
                try:
                    # Analyzer 초기화
                    analyzer = FrequencyDomainAnalyzer(sampling_frequency='D')

                    # 분석 실행
                    summary_df, corr_matrix = analyzer.generate_summary_report(df)

                    # 주파수별 변동성 데이터 수집 (차트용)
                    volatility_data = []
                    for asset in df.columns:
                        vol = analyzer.calculate_volatility_spectral(df[asset])
                        volatility_data.append({
                            '자산': asset,
                            '단기 (5일~3개월)': vol['short_term'] * 100,
                            '중기 (3개월~1년)': vol['medium_term'] * 100,
                            '경기순환 (1~5년)': vol['business_cycle'] * 100,
                            '장기추세 (5년+)': vol['long_term'] * 100
                        })

                    vol_df = pd.DataFrame(volatility_data)

                    # 세션에 저장
                    st.session_state.analysis_results = {
                        'summary': summary_df,
                        'correlation': corr_matrix,
                        'volatility': vol_df,
                        'analyzer': analyzer
                    }

                    st.success('✅ 분석 완료!')

                except Exception as e:
                    st.error(f"❌ 분석 중 오류가 발생했습니다: {str(e)}")
                    st.exception(e)

        # 분석 결과 표시
        if st.session_state.analysis_results is not None:
            st.divider()
            st.header("📈 분석 결과")

            results = st.session_state.analysis_results
            summary_df = results['summary']
            corr_matrix = results['correlation']
            vol_df = results['volatility']

            # 탭 생성
            tab1, tab2, tab3 = st.tabs([
                "📊 요약 통계",
                "📉 변동성 분해",
                "🔗 상관계수"
            ])

            # 탭 1: 요약 통계
            with tab1:
                st.subheader("자산별 기대수익률 및 변동성")

                # 주요 지표 카드 형식으로 표시
                st.markdown("#### 📊 핵심 지표")
                metric_cols = st.columns(len(df.columns))

                for idx, (col, asset) in enumerate(zip(metric_cols, summary_df['Asset'])):
                    with col:
                        row = summary_df[summary_df['Asset'] == asset].iloc[0]
                        st.metric(
                            label=f"**{asset}**",
                            value=f"{row['Expected_Return']*100:.2f}%",
                            delta=f"샤프: {row['Sharpe_Ratio']:.3f}",
                            help=f"변동성: {row['Volatility']*100:.2f}%"
                        )

                st.divider()

                # 표 포맷팅
                st.markdown("#### 📋 상세 통계")
                summary_display = summary_df.copy()
                summary_display['Expected_Return'] = summary_display['Expected_Return'].apply(lambda x: f"{x*100:.2f}%")
                summary_display['Volatility'] = summary_display['Volatility'].apply(lambda x: f"{x*100:.2f}%")
                summary_display['Sharpe_Ratio'] = summary_display['Sharpe_Ratio'].apply(lambda x: f"{x:.3f}")
                summary_display['Short_Term_Vol'] = summary_display['Short_Term_Vol'].apply(lambda x: f"{x*100:.2f}%")
                summary_display['Medium_Term_Vol'] = summary_display['Medium_Term_Vol'].apply(lambda x: f"{x*100:.2f}%")
                summary_display['Business_Cycle_Vol'] = summary_display['Business_Cycle_Vol'].apply(lambda x: f"{x*100:.2f}%")
                summary_display['Long_Term_Vol'] = summary_display['Long_Term_Vol'].apply(lambda x: f"{x*100:.2f}%")

                # 컬럼명 변경
                summary_display.columns = [
                    '자산', '기대수익률(연)', '변동성(연)', '샤프지수',
                    '단기변동성', '중기변동성', '경기순환변동성', '장기변동성'
                ]

                st.dataframe(
                    summary_display,
                    width='stretch',
                    hide_index=True
                )

                # Risk-Return 산점도
                st.markdown("#### 📈 Risk-Return 분석")
                fig_scatter = go.Figure()

                fig_scatter.add_trace(go.Scatter(
                    x=summary_df['Volatility'] * 100,
                    y=summary_df['Expected_Return'] * 100,
                    mode='markers+text',
                    marker=dict(
                        size=15,
                        color=summary_df['Sharpe_Ratio'],
                        colorscale='Viridis',
                        showscale=True,
                        colorbar=dict(title="샤프지수"),
                        line=dict(width=2, color='white')
                    ),
                    text=summary_df['Asset'],
                    textposition="top center",
                    textfont=dict(size=11, family='Malgun Gothic'),
                    hovertemplate='<b>%{text}</b><br>변동성: %{x:.2f}%<br>수익률: %{y:.2f}%<extra></extra>'
                ))

                fig_scatter.update_layout(
                    title='위험 대비 수익률 (Risk-Return Profile)',
                    xaxis_title='변동성 (연율화, %)',
                    yaxis_title='기대수익률 (연율화, %)',
                    height=400,
                    hovermode='closest',
                    font=dict(family='Malgun Gothic', size=12),
                    plot_bgcolor='rgba(240,240,240,0.5)',
                    xaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightGray'),
                    yaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightGray')
                )

                st.plotly_chart(fig_scatter, width="stretch")

                # 해석 가이드
                with st.expander("💡 해석 가이드"):
                    st.markdown("""
                    - **기대수익률**: 연율화된 평균 수익률
                    - **변동성**: 연율화된 표준편차 (리스크 지표)
                    - **샤프지수**: 위험 대비 수익률 (높을수록 좋음)
                    - **단기변동성**: 5일 ~ 3개월 단위 변동 (노이즈)
                    - **중기변동성**: 3개월 ~ 1년 단위 변동 (계절성)
                    - **경기순환변동성**: 1년 ~ 5년 단위 변동 (경기 사이클)
                    - **장기변동성**: 5년 이상 추세 변동

                    **Risk-Return 산점도**: 우상향에 위치할수록 높은 수익률과 낮은 리스크를 의미합니다.
                    """)

            # 탭 2: 변동성 분해 차트
            with tab2:
                st.subheader("주파수 대역별 변동성 분해")

                freq_bands = ['단기 (5일~3개월)', '중기 (3개월~1년)', '경기순환 (1~5년)', '장기추세 (5년+)']

                # 차트 타입 선택
                chart_col1, chart_col2 = st.columns([3, 1])
                with chart_col2:
                    chart_type = st.radio(
                        "차트 유형",
                        ["누적 막대", "그룹 막대", "100% 누적"],
                        horizontal=False
                    )

                # 색상 팔레트 (더 세련된 색상)
                colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']

                with chart_col1:
                    if chart_type == "누적 막대":
                        # 누적 막대 차트
                        fig = go.Figure()
                        for i, band in enumerate(freq_bands):
                            fig.add_trace(go.Bar(
                                name=band,
                                x=vol_df['자산'],
                                y=vol_df[band],
                                marker_color=colors[i],
                                text=vol_df[band].apply(lambda x: f'{x:.1f}%'),
                                textposition='inside',
                                textfont=dict(color='white', size=10)
                            ))

                        fig.update_layout(
                            barmode='stack',
                            title='자산별 주파수 대역별 변동성 분해',
                            xaxis_title='',
                            yaxis_title='변동성 (%)',
                            height=450,
                            hovermode='x unified',
                            font=dict(family='Malgun Gothic', size=12),
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1
                            ),
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                        )
                        fig.update_xaxes(showgrid=False)
                        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')

                    elif chart_type == "그룹 막대":
                        # 그룹 막대 차트
                        fig = go.Figure()
                        for i, band in enumerate(freq_bands):
                            fig.add_trace(go.Bar(
                                name=band,
                                x=vol_df['자산'],
                                y=vol_df[band],
                                marker_color=colors[i],
                                text=vol_df[band].apply(lambda x: f'{x:.1f}%'),
                                textposition='outside',
                                textfont=dict(size=9)
                            ))

                        fig.update_layout(
                            barmode='group',
                            title='자산별 주파수 대역별 변동성 분해',
                            xaxis_title='',
                            yaxis_title='변동성 (%)',
                            height=450,
                            hovermode='x unified',
                            font=dict(family='Malgun Gothic', size=12),
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1
                            ),
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                        )
                        fig.update_xaxes(showgrid=False)
                        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')

                    else:  # 100% 누적
                        # 100% 누적 막대 차트 (비율)
                        vol_ratio_calc = vol_df.copy()
                        total = vol_ratio_calc[freq_bands].sum(axis=1)

                        fig = go.Figure()
                        for i, band in enumerate(freq_bands):
                            ratio = (vol_ratio_calc[band] / total * 100)
                            fig.add_trace(go.Bar(
                                name=band,
                                x=vol_df['자산'],
                                y=ratio,
                                marker_color=colors[i],
                                text=ratio.apply(lambda x: f'{x:.1f}%'),
                                textposition='inside',
                                textfont=dict(color='white', size=10)
                            ))

                        fig.update_layout(
                            barmode='stack',
                            title='자산별 주파수 대역별 변동성 비율 (100% 누적)',
                            xaxis_title='',
                            yaxis_title='비율 (%)',
                            height=450,
                            hovermode='x unified',
                            font=dict(family='Malgun Gothic', size=12),
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1
                            ),
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                        )
                        fig.update_xaxes(showgrid=False)
                        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray', range=[0, 100])

                    st.plotly_chart(fig, width="stretch")

                # 변동성 비율 표 및 인사이트
                col1, col2 = st.columns([1, 1])

                with col1:
                    with st.expander("📊 변동성 절대값 상세보기"):
                        vol_display = vol_df.copy()
                        for band in freq_bands:
                            vol_display[band] = vol_display[band].apply(lambda x: f"{x:.2f}%")
                        st.dataframe(
                            vol_display,
                            width="stretch",
                            hide_index=True
                        )

                with col2:
                    with st.expander("📊 변동성 비율 상세보기"):
                        vol_ratio = vol_df.copy()
                        total = vol_ratio[freq_bands].sum(axis=1)

                        ratio_display = pd.DataFrame({'자산': vol_ratio['자산']})
                        for band in freq_bands:
                            ratio_display[band] = (vol_ratio[band] / total * 100).apply(lambda x: f"{x:.1f}%")

                        st.dataframe(
                            ratio_display,
                            width="stretch",
                            hide_index=True
                        )

                # 인사이트 표시
                st.markdown("### 💡 주요 인사이트")

                # 가장 변동성이 큰 자산
                total_vol = vol_df[freq_bands].sum(axis=1)
                max_vol_asset = vol_df.loc[total_vol.idxmax(), '자산']
                max_vol_value = total_vol.max()

                # 각 주파수 대역에서 가장 큰 비율을 차지하는 자산
                insights = []
                for band in freq_bands:
                    max_asset = vol_df.loc[vol_df[band].idxmax(), '자산']
                    max_value = vol_df[band].max()
                    insights.append(f"**{band}**: {max_asset} ({max_value:.2f}%)")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "가장 변동성 큰 자산",
                        max_vol_asset,
                        f"{max_vol_value:.2f}%"
                    )

                with col2:
                    # 각 자산의 주요 변동성 대역
                    dominant_band = []
                    for idx, row in vol_df.iterrows():
                        band_values = [row[band] for band in freq_bands]
                        dominant = freq_bands[band_values.index(max(band_values))]
                        dominant_band.append(dominant)

                    dominant_info = "**주요 변동성 대역**\n\n"
                    for i in range(len(vol_df)):
                        asset_name = vol_df.loc[i, '자산']
                        band_name = dominant_band[i]
                        dominant_info += f"• **{asset_name}**: {band_name}\n\n"

                    st.info(dominant_info)

                with col3:
                    st.success("**해석 가이드**\n\n• 막대가 높을수록 해당 시간 스케일에서 변동성이 큽니다.\n\n• 주파수 대역별 변동성 분포를 통해 리스크가 어느 시간대에 집중되어 있는지 파악할 수 있습니다.")

            # 탭 3: 상관계수 히트맵
            with tab3:
                st.subheader("자산 간 상관계수 행렬")

                # Plotly 히트맵 (개선된 디자인)
                fig = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.index,
                    colorscale='RdBu_r',
                    zmid=0,
                    zmin=-1,
                    zmax=1,
                    text=corr_matrix.values,
                    texttemplate='%{text:.3f}',
                    textfont={"size": 11, "color": "black"},
                    colorbar=dict(
                        title="상관계수",
                        tickvals=[-1, -0.5, 0, 0.5, 1],
                        ticktext=['-1.0<br>(완전 음)', '-0.5', '0<br>(무상관)', '0.5', '1.0<br>(완전 양)']
                    ),
                    hovertemplate='%{y} ↔ %{x}<br>상관계수: %{z:.3f}<extra></extra>'
                ))

                fig.update_layout(
                    title='자산 간 상관계수 히트맵 (전체 기간)',
                    height=450,
                    font=dict(family='Malgun Gothic', size=12),
                    xaxis=dict(side='bottom'),
                    yaxis=dict(autorange='reversed')
                )

                st.plotly_chart(fig, width="stretch")

                # 상관계수 인사이트
                st.markdown("#### 💡 상관관계 인사이트")

                # 가장 높은 양의 상관관계
                corr_flat = corr_matrix.values.copy()
                np.fill_diagonal(corr_flat, -999)  # 대각선 제외
                max_corr_idx = np.unravel_index(np.argmax(corr_flat), corr_flat.shape)
                max_corr_assets = (corr_matrix.index[max_corr_idx[0]], corr_matrix.columns[max_corr_idx[1]])
                max_corr_value = corr_flat[max_corr_idx]

                # 가장 낮은 음의 상관관계
                min_corr_idx = np.unravel_index(np.argmin(corr_flat), corr_flat.shape)
                min_corr_assets = (corr_matrix.index[min_corr_idx[0]], corr_matrix.columns[min_corr_idx[1]])
                min_corr_value = corr_flat[min_corr_idx]

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.success(f"**가장 높은 양의 상관관계**\n\n{max_corr_assets[0]} ↔ {max_corr_assets[1]}\n\n상관계수: {max_corr_value:.3f}")

                with col2:
                    st.error(f"**가장 낮은 음의 상관관계**\n\n{min_corr_assets[0]} ↔ {min_corr_assets[1]}\n\n상관계수: {min_corr_value:.3f}")

                with col3:
                    st.info("**분산 효과**\n\n음의 상관관계를 가진 자산을 함께 보유하면 포트폴리오 리스크를 줄일 수 있습니다.")

                # 주파수별 상관계수 (선택)
                st.markdown("#### 주파수 대역별 상관계수 분석")

                if len(df.columns) >= 2:
                    col1, col2 = st.columns(2)
                    with col1:
                        asset1 = st.selectbox("자산 1", df.columns, key='asset1')
                    with col2:
                        asset2 = st.selectbox("자산 2", df.columns, index=1 if len(df.columns) > 1 else 0, key='asset2')

                    if asset1 != asset2:
                        analyzer = results['analyzer']
                        freq_corr = analyzer.calculate_correlation_spectral(df[asset1], df[asset2])

                        # 막대 차트
                        freq_corr_df = pd.DataFrame({
                            '주파수 대역': [
                                '단기\n(5일~3개월)',
                                '중기\n(3개월~1년)',
                                '경기순환\n(1~5년)',
                                '장기추세\n(5년+)',
                                '전체'
                            ],
                            '상관계수': [
                                freq_corr['short_term'],
                                freq_corr['medium_term'],
                                freq_corr['business_cycle'],
                                freq_corr['long_term'],
                                freq_corr['total']
                            ]
                        })

                        fig2 = px.bar(
                            freq_corr_df,
                            x='주파수 대역',
                            y='상관계수',
                            title=f'{asset1} vs {asset2} 주파수별 상관계수',
                            color='상관계수',
                            color_continuous_scale='RdBu',
                            range_color=[-1, 1]
                        )

                        fig2.update_layout(
                            height=400,
                            font=dict(family='Malgun Gothic', size=12),
                            showlegend=False
                        )

                        st.plotly_chart(fig2, width="stretch")

                        st.info("""
                        💡 **해석**: 서로 다른 시간 스케일에서 자산 간 상관관계가 어떻게 달라지는지 보여줍니다.
                        위기 시에는 특정 주파수 대역에서 상관관계가 급증할 수 있습니다.
                        """)

            # Excel 다운로드 버튼
            st.divider()
            st.header("💾 결과 다운로드")

            # Excel 파일 생성
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # 요약 통계
                summary_df.to_excel(writer, sheet_name='요약통계', index=False)

                # 상관계수
                corr_matrix.to_excel(writer, sheet_name='상관계수')

                # 변동성 분해
                vol_df.to_excel(writer, sheet_name='변동성분해', index=False)

            excel_data = output.getvalue()

            st.download_button(
                label="📥 Excel 다운로드",
                data=excel_data,
                file_name="frequency_domain_analysis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch"
            )

    except Exception as e:
        st.error(f"❌ 파일을 읽는 중 오류가 발생했습니다: {str(e)}")
        st.exception(e)

else:
    # 파일이 없을 때
    st.info("👈 왼쪽 사이드바에서 CSV 또는 Excel 파일을 업로드하세요.")

    # 샘플 데이터 생성 버튼
    st.markdown("---")
    st.subheader("🧪 샘플 데이터로 테스트")

    if st.button("샘플 데이터 생성", type="secondary"):
        # 샘플 데이터 생성 - 실제 자산 특성 반영
        np.random.seed(42)
        n_days = 252 * 5  # 5년 (주파수 분석을 위해 충분한 기간)
        dates = pd.date_range('2019-01-01', periods=n_days, freq='D')

        # 실제 자산 특성을 반영한 수익률 생성
        # 1. 주식 (KOSPI/S&P500): 연 8-10% 수익률, 변동성 18-20%
        stock_returns = np.random.normal(0.0004, 0.012, n_days)  # 일 0.04%, 연 10.1%, 변동성 19%

        # 2. 채권 (국고채): 연 3-4% 수익률, 변동성 4-6%
        bond_returns = np.random.normal(0.00012, 0.003, n_days)  # 일 0.012%, 연 3.0%, 변동성 4.8%

        # 3. 금 (Gold): 연 5-7% 수익률, 변동성 15-17%
        gold_returns = np.random.normal(0.00025, 0.010, n_days)  # 일 0.025%, 연 6.3%, 변동성 15.9%

        # 4. 원자재 (Commodity): 연 4-6% 수익률, 변동성 20-25%
        commodity_returns = np.random.normal(0.0002, 0.015, n_days)  # 일 0.02%, 연 5.0%, 변동성 23.8%

        # 5. 리츠 (REITs): 연 7-9% 수익률, 변동성 14-16%
        reit_returns = np.random.normal(0.00035, 0.009, n_days)  # 일 0.035%, 연 8.8%, 변동성 14.3%

        # 상관관계 추가 (주식과 채권은 음의 상관관계)
        bond_returns = bond_returns - 0.3 * stock_returns + np.random.normal(0, 0.002, n_days)

        # 금은 위기 시 안전자산으로 주식과 약한 음의 상관관계
        gold_returns = gold_returns - 0.15 * stock_returns + np.random.normal(0, 0.008, n_days)

        # 원자재는 주식과 약한 양의 상관관계
        commodity_returns = commodity_returns + 0.2 * stock_returns + np.random.normal(0, 0.012, n_days)

        # 리츠는 주식과 중간 정도 양의 상관관계
        reit_returns = reit_returns + 0.4 * stock_returns + np.random.normal(0, 0.007, n_days)

        returns_data = {
            '주식': stock_returns,
            '채권': bond_returns,
            '금': gold_returns,
            '원자재': commodity_returns,
            '리츠': reit_returns
        }

        sample_df = pd.DataFrame(returns_data, index=dates)
        st.session_state.returns_df = sample_df
        st.rerun()

# 푸터
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>주파수 영역 자산 분석 시스템 v1.0 | Ortec Finance 방법론 기반</p>
</div>
""", unsafe_allow_html=True)
