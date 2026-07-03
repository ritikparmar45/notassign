import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from app.models.analytics import Analytics
from app.models.notification import NotificationStatus

logger = logging.getLogger(__name__)

class AnalyticsService:
    """
    Service layer for logging and retrieving analytics metrics.
    """
    @staticmethod
    async def record_event(channel: str, status: str) -> Analytics:
        """
        Creates a delivery analytics record.
        """
        event = Analytics(channel=channel.lower(), status=status)
        await event.insert()
        return event

    @staticmethod
    async def get_statistics() -> Dict[str, Any]:
        """
        Computes summary statistics and breakdowns by channel using aggregation pipelines.
        """
        # Overall status counts
        overall_pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        overall_results = await Analytics.aggregate(overall_pipeline).to_list()
        
        overall_counts = {
            "Sent": 0,
            "Delivered": 0,
            "Failed": 0,
            "Skipped": 0
        }
        for item in overall_results:
            status_val = item["_id"]
            if status_val in overall_counts:
                overall_counts[status_val] = item["count"]

        total_processed = sum(overall_counts.values())

        # Channel specific breakdowns
        channel_pipeline = [
            {
                "$group": {
                    "_id": {
                        "channel": "$channel",
                        "status": "$status"
                    },
                    "count": {"$sum": 1}
                }
            }
        ]
        channel_results = await Analytics.aggregate(channel_pipeline).to_list()

        channel_breakdown: Dict[str, Dict[str, int]] = {
            "email": {"Sent": 0, "Delivered": 0, "Failed": 0, "Skipped": 0},
            "sms": {"Sent": 0, "Delivered": 0, "Failed": 0, "Skipped": 0},
            "push": {"Sent": 0, "Delivered": 0, "Failed": 0, "Skipped": 0}
        }

        for item in channel_results:
            grp = item["_id"]
            ch = grp["channel"]
            st = grp["status"]
            if ch in channel_breakdown and st in channel_breakdown[ch]:
                channel_breakdown[ch][st] = item["count"]

        # Calculate success rates per channel
        # Success Rate = Delivered / (Delivered + Failed) or Delivered / Total
        channel_metrics = {}
        for ch, counts in channel_breakdown.items():
            ch_delivered = counts["Delivered"]
            ch_failed = counts["Failed"]
            ch_sent = counts["Sent"]
            ch_total = ch_delivered + ch_failed + ch_sent + counts["Skipped"]
            
            # Successful attempts vs active sends
            active_attempts = ch_delivered + ch_failed
            success_rate = 0.0
            if active_attempts > 0:
                success_rate = round((ch_delivered / active_attempts) * 100, 2)

            channel_metrics[ch] = {
                "counts": counts,
                "total_requests": ch_total,
                "success_rate_percent": success_rate
            }

        # Daily trends for the last 7 days
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        trend_pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": seven_days_ago}
                }
            },
            {
                "$project": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                    "status": "$status"
                }
            },
            {
                "$group": {
                    "_id": {
                        "date": "$date",
                        "status": "$status"
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id.date": 1}
            }
        ]
        trend_results = await Analytics.aggregate(trend_pipeline).to_list()
        
        daily_trends: Dict[str, Dict[str, int]] = {}
        for item in trend_results:
            date_str = item["_id"]["date"]
            status_val = item["_id"]["status"]
            count = item["count"]
            if date_str not in daily_trends:
                daily_trends[date_str] = {"Delivered": 0, "Failed": 0}
            if status_val in daily_trends[date_str]:
                daily_trends[date_str][status_val] = count

        return {
            "summary": {
                "total_processed": total_processed,
                "overall_status_counts": overall_counts,
                "overall_success_rate_percent": round(
                    (overall_counts["Delivered"] / (overall_counts["Delivered"] + overall_counts["Failed"]) * 100) 
                    if (overall_counts["Delivered"] + overall_counts["Failed"]) > 0 else 0.0, 
                    2
                )
            },
            "channel_breakdown": channel_metrics,
            "last_7_days_trend": daily_trends
        }
