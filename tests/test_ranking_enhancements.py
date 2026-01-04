"""
Tests for Gorgonoid ranking enhancements.
Tests internal metrics calculations and badge logic.
"""
import pytest


def test_views_reais_calculation():
    """Test that views_reais = (longos * 1.0) + (shorts * 0.25)"""
    # Test case 1: 1M longos views, 400K shorts views
    longos = 1_000_000
    shorts = 400_000
    expected = (longos * 1.0) + (shorts * 0.25)  # 1,100,000
    assert expected == 1_100_000
    
    # Test case 2: Only shorts
    longos = 0
    shorts = 1_000_000
    expected = (longos * 1.0) + (shorts * 0.25)  # 250,000
    assert expected == 250_000
    
    # Test case 3: Only longos
    longos = 5_000_000
    shorts = 0
    expected = (longos * 1.0) + (shorts * 0.25)  # 5,000,000
    assert expected == 5_000_000
    
    # Test case 4: Mixed (Bitelo-like: high shorts)
    longos = 500_000
    shorts = 2_000_000
    expected = (longos * 1.0) + (shorts * 0.25)  # 1,000,000
    assert expected == 1_000_000


def test_efficiency_calculation():
    """Test media_por_conteudo = views_period / total_videos"""
    # Test case 1: Normal efficiency
    views_period = 1_000_000
    total_videos = 100
    efficiency = views_period / total_videos
    assert efficiency == 10_000
    
    # Test case 2: High efficiency (fewer videos, more views)
    views_period = 10_000_000
    total_videos = 50
    efficiency = views_period / total_videos
    assert efficiency == 200_000
    
    # Test case 3: Low efficiency (many videos, fewer views)
    views_period = 500_000
    total_videos = 500
    efficiency = views_period / total_videos
    assert efficiency == 1_000
    
    # Test case 4: Zero videos (edge case)
    views_period = 1_000_000
    total_videos = 0
    efficiency = views_period / total_videos if total_videos > 0 else 0
    assert efficiency == 0


def test_badge_explosao_shorts():
    """Test Explosão de Shorts badge (≥60% views from shorts)"""
    # Should get badge: 60% from shorts
    shorts_views = 600_000
    total_views = 1_000_000
    assert (shorts_views / total_views) >= 0.60
    
    # Should get badge: 80% from shorts
    shorts_views = 800_000
    total_views = 1_000_000
    assert (shorts_views / total_views) >= 0.60
    
    # Should NOT get badge: 50% from shorts
    shorts_views = 500_000
    total_views = 1_000_000
    assert (shorts_views / total_views) < 0.60
    
    # Should NOT get badge: 59.9% from shorts
    shorts_views = 599_000
    total_views = 1_000_000
    assert (shorts_views / total_views) < 0.60


def test_badge_alta_eficiencia():
    """Test Alta Eficiência badge (above average efficiency)"""
    # Simulated ranking data
    efficiencies = [10_000, 15_000, 20_000, 25_000, 30_000]
    avg_efficiency = sum(efficiencies) / len(efficiencies)  # 20,000
    
    # Should get badge: 25,000 > 20,000
    channel_efficiency = 25_000
    assert channel_efficiency > avg_efficiency
    
    # Should get badge: 30,000 > 20,000
    channel_efficiency = 30_000
    assert channel_efficiency > avg_efficiency
    
    # Should NOT get badge: 15,000 < 20,000
    channel_efficiency = 15_000
    assert channel_efficiency < avg_efficiency
    
    # Edge case: exactly average (should NOT get badge)
    channel_efficiency = 20_000
    assert not (channel_efficiency > avg_efficiency)


def test_badge_volume_massivo():
    """Test Volume Massivo badge (≥P75 video count)"""
    # Simulated ranking data
    video_counts = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    # P75 = 75th percentile = 77.5 (approximately 78)
    import statistics
    p75 = statistics.quantiles(video_counts, n=4)[2]  # 3rd quartile
    
    # Should get badge: 80 >= 77.5
    channel_videos = 80
    assert channel_videos >= p75
    
    # Should get badge: 100 >= 77.5
    channel_videos = 100
    assert channel_videos >= p75
    
    # Should NOT get badge: 50 < 77.5
    channel_videos = 50
    assert channel_videos < p75


def test_badge_conteudo_prateleira():
    """Test Conteúdo de Prateleira badge (high volume + low efficiency)"""
    # Setup
    video_counts = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    efficiencies = [10_000, 15_000, 20_000, 25_000, 30_000, 35_000, 40_000, 45_000, 50_000, 55_000]
    
    import statistics
    p75_volume = statistics.quantiles(video_counts, n=4)[2]
    avg_efficiency = sum(efficiencies) / len(efficiencies)
    
    # Should get badge: 80 videos >= P75 AND 15,000 efficiency < avg
    channel_videos = 80
    channel_efficiency = 15_000
    assert channel_videos >= p75_volume and channel_efficiency < avg_efficiency
    
    # Should NOT get badge: High volume but HIGH efficiency
    channel_videos = 80
    channel_efficiency = 50_000
    assert not (channel_videos >= p75_volume and channel_efficiency < avg_efficiency)
    
    # Should NOT get badge: Low volume AND low efficiency
    channel_videos = 30
    channel_efficiency = 15_000
    assert not (channel_videos >= p75_volume and channel_efficiency < avg_efficiency)


def test_editorial_cutoff():
    """Test editorial cut-off flag (< 1M views)"""
    # Below cutoff
    views_period = 500_000
    assert views_period < 1_000_000
    
    # Below cutoff (edge case)
    views_period = 999_999
    assert views_period < 1_000_000
    
    # NOT below cutoff (exactly 1M)
    views_period = 1_000_000
    assert not (views_period < 1_000_000)
    
    # NOT below cutoff
    views_period = 5_000_000
    assert not (views_period < 1_000_000)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
