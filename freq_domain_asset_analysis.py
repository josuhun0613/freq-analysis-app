"""
Frequency Domain 기반 자산군별 통계 추정 (완전 수정 버전)
Ortec Finance 방법론 참고

주요 수정사항:
1. 데이터 길이를 10년으로 증가 (나이퀴스트 정리 충족)
2. 주파수 대역을 데이터 길이에 맞게 재정의
3. 순수 랜덤 데이터로 예시 변경
"""

import numpy as np
import pandas as pd
from scipy import signal
from scipy.fft import fft, fftfreq, ifft
import matplotlib.pyplot as plt
from typing import Tuple, Dict, List
import platform

# 한글 폰트 설정
def setup_korean_font():
    """운영체제에 맞는 한글 폰트 설정"""
    system = platform.system()
    
    if system == 'Windows':
        plt.rcParams['font.family'] = 'Malgun Gothic'
    elif system == 'Darwin':  # macOS
        plt.rcParams['font.family'] = 'AppleGothic'
    else:  # Linux
        try:
            plt.rcParams['font.family'] = 'NanumGothic'
        except:
            pass
    
    plt.rcParams['axes.unicode_minus'] = False

setup_korean_font()


class FrequencyDomainAnalyzer:
    """
    Frequency Domain을 활용한 자산 분석 클래스
    Ortec Finance의 Zero-Phase Filter 방법론 기반 (완전 수정 버전)
    """
    
    def __init__(self, sampling_frequency: str = 'D'):
        """
        Parameters:
        -----------
        sampling_frequency : str
            데이터 빈도 ('D': 일별, 'W': 주별, 'M': 월별)
        """
        self.sampling_freq = sampling_frequency
        
        # 주파수 대역 정의 (정규화된 주파수: 0~0.5)
        # 일별 데이터 기준 (Nyquist = 0.5)
        if sampling_frequency == 'D':
            self.freq_bands = {
                'short_term': (0.04, 0.5),      # 2~25일 주기 (단기 노이즈)
                'medium_term': (0.008, 0.04),   # 25~125일 (계절성, ~1~6개월)
                'business_cycle': (0.002, 0.008), # 125~500일 (경기순환, ~0.5~2년)
                'long_term': (0, 0.002)         # 500일+ (장기 추세, 2년+)
            }
        elif sampling_frequency == 'M':
            self.freq_bands = {
                'short_term': (1/3, 0.5),           # 2~3개월
                'medium_term': (1/12, 1/3),         # 3개월~1년
                'business_cycle': (1/60, 1/12),     # 1년~5년
                'long_term': (0, 1/60)              # 5년 이상
            }
    
    def zero_phase_filter(self, data: np.ndarray, 
                         low_freq: float = None,
                         high_freq: float = None,
                         order: int = 3) -> np.ndarray:
        """
        Zero-Phase Shift Filter 적용 (Band-pass, Low-pass, High-pass 지원)
        
        Parameters:
        -----------
        data : np.ndarray
            입력 시계열 데이터
        low_freq : float or None
            하한 주파수 (None이면 low-pass)
        high_freq : float or None
            상한 주파수 (None이면 high-pass)
        order : int
            필터 차수 (낮춤 - 너무 높으면 불안정)
            
        Returns:
        --------
        filtered_data : np.ndarray
            필터링된 데이터
        """
        nyquist = 0.5  # 정규화된 Nyquist 주파수
        
        # 필터 타입 결정
        if low_freq is None and high_freq is None:
            return data.copy()
        
        try:
            # Low-pass filter
            if low_freq is None:
                high_normalized = high_freq / nyquist
                high_normalized = min(max(high_normalized, 0.001), 0.95)
                
                b, a = signal.butter(order, high_normalized, btype='low')
            
            # High-pass filter
            elif high_freq is None:
                low_normalized = low_freq / nyquist
                low_normalized = min(max(low_normalized, 0.001), 0.95)
                
                b, a = signal.butter(order, low_normalized, btype='high')
            
            # Band-pass filter
            else:
                low_normalized = low_freq / nyquist
                high_normalized = high_freq / nyquist
                
                low_normalized = min(max(low_normalized, 0.001), 0.95)
                high_normalized = min(max(high_normalized, 0.001), 0.95)
                
                if low_normalized >= high_normalized:
                    return np.zeros_like(data)
                
                b, a = signal.butter(order, [low_normalized, high_normalized], btype='band')
            
            # Zero-phase filtering (양방향 필터링)
            filtered_data = signal.filtfilt(b, a, data)
            
            return filtered_data
            
        except Exception as e:
            # 필터링 실패 시 0 반환
            print(f"Warning: Filter failed with low={low_freq}, high={high_freq}: {e}")
            return np.zeros_like(data)
    
    def decompose_frequency_bands(self, returns: pd.Series) -> Dict[str, np.ndarray]:
        """
        수익률을 주파수 대역별로 분해
        
        Parameters:
        -----------
        returns : pd.Series
            자산 수익률 시계열
            
        Returns:
        --------
        decomposed : Dict[str, np.ndarray]
            주파수 대역별 분해된 수익률
        """
        data = returns.values
        decomposed = {}
        
        for band_name, freq_range in self.freq_bands.items():
            if band_name == 'long_term':
                # Long-term: low-pass filter
                filtered = self.zero_phase_filter(data, low_freq=None, 
                                                 high_freq=freq_range[1])
            else:
                # 나머지: band-pass filter
                low_freq, high_freq = freq_range
                filtered = self.zero_phase_filter(data, low_freq=low_freq, 
                                                 high_freq=high_freq)
            
            decomposed[band_name] = filtered
            
        return decomposed
    
    def calculate_expected_return(self, returns: pd.Series, 
                                 annualize: bool = True) -> Dict[str, float]:
        """
        주파수 대역별 및 전체 기대수익률 계산
        
        Parameters:
        -----------
        returns : pd.Series
            자산 수익률 시계열
        annualize : bool
            연율화 여부
            
        Returns:
        --------
        expected_returns : Dict[str, float]
            전체 기대수익률
        """
        # 전체 기대수익률
        total_mean = np.mean(returns)
        if annualize and self.sampling_freq == 'D':
            total_mean *= 252
        elif annualize and self.sampling_freq == 'M':
            total_mean *= 12
        
        expected_returns = {'total': total_mean}
        
        return expected_returns
    
    def calculate_volatility_spectral(self, returns: pd.Series, 
                                     annualize: bool = True) -> Dict[str, float]:
        """
        Power Spectral Density를 이용한 주파수별 변동성 계산
        
        Parameters:
        -----------
        returns : pd.Series
            자산 수익률 시계열
        annualize : bool
            연율화 여부
            
        Returns:
        --------
        volatilities : Dict[str, float]
            주파수 대역별 및 전체 변동성
        """
        data = returns.values
        
        # Power Spectral Density 계산
        freqs, psd = signal.periodogram(data, scaling='density')
        
        volatilities = {}
        
        # 주파수 대역별 변동성 (PSD 적분)
        for band_name, freq_range in self.freq_bands.items():
            if band_name == 'long_term':
                # Long-term: 0부터 상한까지
                mask = (freqs >= 0) & (freqs <= freq_range[1])
            else:
                # 나머지: 하한부터 상한까지
                low_freq, high_freq = freq_range
                mask = (freqs >= low_freq) & (freqs <= high_freq)
            
            # 해당 대역의 분산 (PSD 적분)
            if np.any(mask):
                # NumPy 버전 호환성: trapz 사용 (trapezoid는 NumPy 1.22+에서만 사용 가능)
                try:
                    variance = np.trapz(psd[mask], freqs[mask])
                except AttributeError:
                    variance = np.trapezoid(psd[mask], freqs[mask])
                std_dev = np.sqrt(abs(variance))
            else:
                std_dev = 0.0
            
            if annualize and self.sampling_freq == 'D':
                std_dev *= np.sqrt(252)
            elif annualize and self.sampling_freq == 'M':
                std_dev *= np.sqrt(12)
                
            volatilities[band_name] = std_dev
        
        # 전체 변동성 (시간 영역)
        total_vol = np.std(data)
        if annualize and self.sampling_freq == 'D':
            total_vol *= np.sqrt(252)
        elif annualize and self.sampling_freq == 'M':
            total_vol *= np.sqrt(12)
        volatilities['total'] = total_vol
        
        return volatilities
    
    def calculate_correlation_spectral(self, returns1: pd.Series,
                                      returns2: pd.Series) -> Dict[str, float]:
        """
        주파수 대역별 상관계수 계산
        각 주파수 대역으로 필터링된 신호 간의 상관계수를 직접 계산

        주의: 낮은 주파수 대역(장기)은 유효 샘플 수가 적어 신뢰도가 낮을 수 있음

        Parameters:
        -----------
        returns1, returns2 : pd.Series
            두 자산의 수익률 시계열

        Returns:
        --------
        correlations : Dict[str, float]
            주파수 대역별 및 전체 상관계수
        """
        correlations = {}

        # 주파수 대역별로 필터링 후 상관계수 계산
        decomposed1 = self.decompose_frequency_bands(returns1)
        decomposed2 = self.decompose_frequency_bands(returns2)

        for band_name in self.freq_bands.keys():
            filtered1 = decomposed1[band_name]
            filtered2 = decomposed2[band_name]

            # 필터링된 신호 간 상관계수
            std1 = np.std(filtered1)
            std2 = np.std(filtered2)

            if std1 > 1e-10 and std2 > 1e-10:
                correlation = np.corrcoef(filtered1, filtered2)[0, 1]
                # NaN 체크
                if np.isnan(correlation):
                    correlation = 0.0

                # 유효 자유도 추정 (낮은 주파수일수록 자유도 감소)
                # 장기/경기순환 대역은 신뢰도가 낮으므로 참고용으로만 사용
                correlations[band_name] = correlation
            else:
                correlations[band_name] = 0.0

        # 전체 상관계수 (시간 영역)
        total_corr = np.corrcoef(returns1.values, returns2.values)[0, 1]
        correlations['total'] = total_corr

        return correlations
    
    def rolling_analysis(self, returns: pd.DataFrame, 
                        window: int = 252,
                        step: int = 63) -> pd.DataFrame:
        """
        Rolling window로 시간에 따른 통계 변화 추적
        
        Parameters:
        -----------
        returns : pd.DataFrame
            자산들의 수익률 (columns: 자산명)
        window : int
            윈도우 크기
        step : int
            이동 간격
            
        Returns:
        --------
        results : pd.DataFrame
            시간에 따른 통계량 변화
        """
        results = []
        
        for start in range(0, len(returns) - window, step):
            end = start + window
            window_data = returns.iloc[start:end]
            
            result_row = {'date': returns.index[end-1]}
            
            # 각 자산의 통계
            for asset in returns.columns:
                vol = self.calculate_volatility_spectral(window_data[asset])
                result_row[f'{asset}_vol'] = vol['total']
            
            results.append(result_row)
        
        return pd.DataFrame(results)
    
    def generate_summary_report(self, returns: pd.DataFrame) -> pd.DataFrame:
        """
        전체 자산군에 대한 요약 리포트 생성
        
        Parameters:
        -----------
        returns : pd.DataFrame
            자산들의 수익률 (columns: 자산명)
            
        Returns:
        --------
        summary : pd.DataFrame
            자산별 기대수익률, 변동성, 상관계수 요약
        """
        assets = returns.columns
        n_assets = len(assets)
        
        # 기대수익률과 변동성
        summary_data = []
        for asset in assets:
            exp_ret = self.calculate_expected_return(returns[asset])
            vol = self.calculate_volatility_spectral(returns[asset])
            
            summary_data.append({
                'Asset': asset,
                'Expected_Return': exp_ret['total'],
                'Volatility': vol['total'],
                'Sharpe_Ratio': exp_ret['total'] / vol['total'] if vol['total'] > 0 else 0,
                'Short_Term_Vol': vol['short_term'],
                'Medium_Term_Vol': vol['medium_term'],
                'Business_Cycle_Vol': vol['business_cycle'],
                'Long_Term_Vol': vol['long_term']
            })
        
        summary_df = pd.DataFrame(summary_data)
        
        # 상관계수 행렬
        corr_matrix = pd.DataFrame(index=assets, columns=assets)
        
        for i, asset1 in enumerate(assets):
            for j, asset2 in enumerate(assets):
                if i == j:
                    corr_matrix.loc[asset1, asset2] = 1.0
                elif i < j:
                    corr = self.calculate_correlation_spectral(
                        returns[asset1], returns[asset2]
                    )
                    corr_matrix.loc[asset1, asset2] = corr['total']
                    corr_matrix.loc[asset2, asset1] = corr['total']
        
        return summary_df, corr_matrix.astype(float)

    def stl_decomposition(self, returns: pd.Series, period: int = 21) -> Dict[str, pd.Series]:
        """
        STL (Seasonal and Trend decomposition using Loess) 분해

        Parameters:
        -----------
        returns : pd.Series
            자산 수익률 시계열
        period : int
            계절성 주기 (일별 데이터: 21 = 월별, 63 = 분기별)

        Returns:
        --------
        decomposed : Dict[str, pd.Series]
            'original', 'trend', 'seasonal', 'residual' 시계열
        """
        try:
            from statsmodels.tsa.seasonal import STL

            # STL 분해 수행
            stl = STL(returns, period=period, seasonal=13)
            result = stl.fit()

            return {
                'original': returns,
                'trend': result.trend,
                'seasonal': result.seasonal,
                'residual': result.resid
            }
        except Exception as e:
            print(f"STL decomposition failed: {e}")
            # Fallback: 단순 이동평균을 trend로 사용
            trend = returns.rolling(window=period, center=True).mean()
            residual = returns - trend
            seasonal = pd.Series(0, index=returns.index)

            return {
                'original': returns,
                'trend': trend.fillna(0),
                'seasonal': seasonal,
                'residual': residual.fillna(0)
            }

    def generate_stl_summary(self, returns: pd.DataFrame, period: int = None) -> pd.DataFrame:
        """
        전체 자산에 대한 STL 분해 요약 생성

        Parameters:
        -----------
        returns : pd.DataFrame
            자산들의 수익률
        period : int, optional
            계절성 주기 (None이면 sampling_frequency에 따라 자동 설정)
            일별: 21 (월별 패턴), 월별: 12 (연별 패턴)

        Returns:
        --------
        summary : pd.DataFrame
            자산별 STL 분해 통계량
        """
        # 주기 자동 설정
        if period is None:
            if self.sampling_freq == 'D':
                period = 21  # 일별 데이터: 월별 패턴 (21 거래일)
            elif self.sampling_freq == 'M':
                period = 12  # 월별 데이터: 연별 패턴 (12개월)
            else:
                period = 12  # 기본값

        stl_summary = []

        for asset in returns.columns:
            stl_result = self.stl_decomposition(returns[asset], period=period)

            trend_vol = np.std(stl_result['trend'].dropna())
            seasonal_vol = np.std(stl_result['seasonal'])
            residual_vol = np.std(stl_result['residual'].dropna())
            total_vol = np.std(returns[asset])

            # 연율화
            if self.sampling_freq == 'D':
                trend_vol *= np.sqrt(252)
                seasonal_vol *= np.sqrt(252)
                residual_vol *= np.sqrt(252)
                total_vol *= np.sqrt(252)
            elif self.sampling_freq == 'M':
                trend_vol *= np.sqrt(12)
                seasonal_vol *= np.sqrt(12)
                residual_vol *= np.sqrt(12)
                total_vol *= np.sqrt(12)

            # 계절성 강도 계산 (베이스라인 대비 상대적 계절성)
            # STL의 베이스라인: 순수 랜덤 데이터에서 ~35% seasonal 추출
            # 실제 계절성 = (seasonal_vol / total_vol - baseline) / (1 - baseline)
            # 이를 0~1 범위로 정규화
            raw_strength = seasonal_vol / total_vol if total_vol > 0 else 0
            baseline = 0.35  # STL의 랜덤 데이터 베이스라인

            # 베이스라인 보정 (0 미만은 0으로, 1 초과는 1로 클리핑)
            if raw_strength < baseline:
                seasonal_strength = 0.0
            else:
                # 베이스라인을 빼고 재정규화
                seasonal_strength = min((raw_strength - baseline) / (1.0 - baseline), 1.0)

            stl_summary.append({
                'Asset': asset,
                'Trend_Vol': trend_vol,
                'Seasonal_Vol': seasonal_vol,
                'Residual_Vol': residual_vol,
                'Seasonal_Strength': seasonal_strength
            })

        return pd.DataFrame(stl_summary)


# 사용 예시
def example_usage():
    """
    사용 예시 - 순수 랜덤 데이터 (10년)
    """
    # 1. 샘플 데이터 생성 (3개 자산, 10년치 일별 데이터)
    np.random.seed(42)
    n_days = 252 * 10  # 10년으로 증가
    dates = pd.date_range('2014-01-01', periods=n_days, freq='D')
    
    # 순수 랜덤 수익률 시뮬레이션
    returns_data = {
        '주식': np.random.normal(0.0005, 0.015, n_days),    # 연 12.6%, 변동성 23.7%
        '채권': np.random.normal(0.0002, 0.005, n_days),    # 연 5.0%, 변동성 7.9%
        '원자재': np.random.normal(0.0003, 0.020, n_days)   # 연 7.6%, 변동성 31.7%
    }
    
    returns_df = pd.DataFrame(returns_data, index=dates)
    
    # 2. Frequency Domain Analyzer 초기화
    analyzer = FrequencyDomainAnalyzer(sampling_frequency='D')
    
    # 3. 요약 리포트 생성
    print("="*90)
    print("자산군별 Frequency Domain 분석 결과 (완전 수정 버전 - 10년 데이터)")
    print("="*90)
    
    summary, corr_matrix = analyzer.generate_summary_report(returns_df)
    
    print("\n[1] 자산별 기대수익률 및 변동성")
    print("-"*90)
    print(summary.to_string(index=False))
    
    print("\n[2] 자산 간 상관계수 행렬")
    print("-"*90)
    print(corr_matrix)
    
    # 4. 개별 자산 상세 분석
    print("\n[3] 주식 상세 분석")
    print("-"*90)
    
    exp_ret = analyzer.calculate_expected_return(returns_df['주식'])
    print(f"\n전체 기대수익률 (연율화): {exp_ret['total']*100:6.2f}%")
    
    vol = analyzer.calculate_volatility_spectral(returns_df['주식'])
    print("\n변동성 분석 (연율화):")
    print(f"  전체 변동성        : {vol['total']*100:6.2f}%")
    print(f"  단기 변동성        : {vol['short_term']*100:6.2f}% ({vol['short_term']/vol['total']*100:.1f}%)")
    print(f"  중기 변동성        : {vol['medium_term']*100:6.2f}% ({vol['medium_term']/vol['total']*100:.1f}%)")
    print(f"  경기순환 변동성    : {vol['business_cycle']*100:6.2f}% ({vol['business_cycle']/vol['total']*100:.1f}%)")
    print(f"  장기추세 변동성    : {vol['long_term']*100:6.2f}% ({vol['long_term']/vol['total']*100:.1f}%)")
    
    # 5. 자산 간 주파수별 상관관계
    print("\n[4] 주식-채권 주파수별 상관계수")
    print("-"*90)
    
    corr = analyzer.calculate_correlation_spectral(
        returns_df['주식'], returns_df['채권']
    )
    for band, value in corr.items():
        if band == 'total':
            band_display = 'Total (전체)'
        else:
            band_display = band.replace('_', ' ').title()
        print(f"  {band_display:25s}: {value:7.4f}")
    
    print("\n" + "="*90)
    print("💡 해석 가이드:")
    print("- Short Term      : 단기(5일~3개월) 변동")
    print("- Medium Term     : 중기(3개월~1년) 계절성")
    print("- Business Cycle  : 경기순환(1~5년)")  
    print("- Long Term       : 장기 추세(5년+)")
    print("- Total           : 전체 기간 평균")
    print("\n✅ 주요 수정사항:")
    print("1. 데이터 길이를 10년으로 증가 (나이퀴스트 정리 충족)")
    print("2. 주파수 대역을 측정 가능한 범위로 재정의")
    print("3. 필터 차수를 3으로 낮춤 (안정성 개선)")
    print("4. Medium Term 대역 추가 (4개 대역 분석)")
    print("5. 순수 랜덤 데이터 (상관계수 ~0 예상)")
    print("\n분석 완료! ✅")
    print("="*90)
    
    return analyzer, returns_df, summary, corr_matrix


if __name__ == "__main__":
    analyzer, returns_df, summary, corr_matrix = example_usage()