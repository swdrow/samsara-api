#!/usr/bin/env python3
"""
Test the timestamp matching fix
"""

def test_timestamp_matching():
    """Test that the updated timestamp matching works"""
    print("=" * 60)
    print(" TESTING TIMESTAMP MATCHING FIX")
    print("=" * 60)
    
    try:
        from app.tasks import update_extended_forecast_scores_job
        from app.extensions import redis_client
        
        # Run the extended forecast job which should now use NOAA data
        print("Running extended forecast scores job...")
        update_extended_forecast_scores_job()
        
        # Check the results
        extended_scores_str = redis_client.get('extended_forecast_scores_simple')
        if extended_scores_str:
            import json
            extended_scores = json.loads(extended_scores_str)
            
            noaa_count = sum(1 for score in extended_scores if score.get('noaaDataUsed', False))
            total_count = len(extended_scores)
            
            print(f"✓ Extended forecast scores generated: {total_count}")
            print(f"✓ Scores using NOAA data: {noaa_count}")
            print(f"✓ NOAA utilization: {(noaa_count/total_count)*100:.1f}%" if total_count > 0 else "0%")
            
            if noaa_count > 0:
                print("🎉 Timestamp matching is working!")
                return True
            else:
                print("❌ Still no NOAA data being used")
                return False
        else:
            print("❌ No extended forecast scores found")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_timestamp_matching()
    if success:
        print("\nTimestamp matching fix successful!")
    else:
        print("\nTimestamp matching still needs work.")
