
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from models import Campaign, EmailLog, SMSLog, CallLog
from datetime import datetime, timedelta

analytics_bp = Blueprint("analytics", __name__)

@analytics_bp.route("/api/analytics/dashboard")
@login_required
def get_dashboard_analytics():
    """Get dashboard analytics data"""
    try:
        # Date ranges
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Total counts for current user's campaigns
        user_campaign_ids = [c.id for c in Campaign.query.filter_by(created_by=current_user.id).all()]
        
        analytics = {
            "totals": {
                "campaigns": len(user_campaign_ids),
                "emails_sent": EmailLog.query.filter(
                    EmailLog.campaign_id.in_(user_campaign_ids),
                    EmailLog.status == "sent"
                ).count(),
                "sms_sent": SMSLog.query.filter(
                    SMSLog.campaign_id.in_(user_campaign_ids),
                    SMSLog.status == "sent"
                ).count(),
                "calls_made": CallLog.query.filter(
                    CallLog.campaign_id.in_(user_campaign_ids),
                    CallLog.status == "connected"
                ).count()
            },
            "recent": {
                "campaigns_this_week": Campaign.query.filter(
                    Campaign.created_by == current_user.id,
                    Campaign.created_at >= week_ago
                ).count(),
                "emails_this_week": EmailLog.query.filter(
                    EmailLog.campaign_id.in_(user_campaign_ids),
                    EmailLog.sent_at >= week_ago,
                    EmailLog.status == "sent"
                ).count(),
                "sms_this_week": SMSLog.query.filter(
                    SMSLog.campaign_id.in_(user_campaign_ids),
                    SMSLog.sent_at >= week_ago,
                    SMSLog.status == "sent"
                ).count(),
                "calls_this_week": CallLog.query.filter(
                    CallLog.campaign_id.in_(user_campaign_ids),
                    CallLog.called_at >= week_ago,
                    CallLog.status == "connected"
                ).count()
            },
            "success_rates": {
                "email_success_rate": 0,
                "sms_success_rate": 0,
                "call_success_rate": 0
            }
        }
        
        # Calculate success rates
        if user_campaign_ids:
            total_emails = EmailLog.query.filter(EmailLog.campaign_id.in_(user_campaign_ids)).count()
            if total_emails > 0:
                analytics["success_rates"]["email_success_rate"] = round(
                    (analytics["totals"]["emails_sent"] / total_emails) * 100, 1
                )
            
            total_sms = SMSLog.query.filter(SMSLog.campaign_id.in_(user_campaign_ids)).count()
            if total_sms > 0:
                analytics["success_rates"]["sms_success_rate"] = round(
                    (analytics["totals"]["sms_sent"] / total_sms) * 100, 1
                )
            
            total_calls = CallLog.query.filter(CallLog.campaign_id.in_(user_campaign_ids)).count()
            if total_calls > 0:
                analytics["success_rates"]["call_success_rate"] = round(
                    (analytics["totals"]["calls_made"] / total_calls) * 100, 1
                )
        
        return jsonify({
            "success": True,
            "analytics": analytics
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@analytics_bp.route("/api/analytics/campaign-performance")
@login_required
def get_campaign_performance():
    """Get performance data for all user campaigns"""
    try:
        campaigns = Campaign.query.filter_by(created_by=current_user.id).all()
        performance_data = []
        
        for campaign in campaigns:
            # Get counts for this campaign
            emails_sent = EmailLog.query.filter_by(campaign_id=campaign.id, status="sent").count()
            emails_failed = EmailLog.query.filter_by(campaign_id=campaign.id, status="failed").count()
            
            sms_sent = SMSLog.query.filter_by(campaign_id=campaign.id, status="sent").count()
            sms_failed = SMSLog.query.filter_by(campaign_id=campaign.id, status="failed").count()
            
            calls_connected = CallLog.query.filter_by(campaign_id=campaign.id, status="connected").count()
            calls_failed = CallLog.query.filter_by(campaign_id=campaign.id, status="failed").count()
            
            performance_data.append({
                "campaign_id": campaign.id,
                "campaign_name": campaign.name,
                "status": campaign.status,
                "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
                "launched_at": campaign.launched_at.isoformat() if campaign.launched_at else None,
                "metrics": {
                    "email": {"sent": emails_sent, "failed": emails_failed},
                    "sms": {"sent": sms_sent, "failed": sms_failed},
                    "calls": {"connected": calls_connected, "failed": calls_failed}
                }
            })
        
        return jsonify({
            "success": True,
            "campaigns": performance_data
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@analytics_bp.route("/api/campaign/<int:campaign_id>/logs")
@login_required
def get_campaign_logs(campaign_id):
    """Get detailed logs for a specific campaign"""
    try:
        # Verify campaign belongs to user
        campaign = Campaign.query.filter_by(id=campaign_id, created_by=current_user.id).first()
        if not campaign:
            return jsonify({"success": False, "error": "Campaign not found"}), 404
        
        # Get all logs for this campaign
        email_logs = [log.to_dict() for log in EmailLog.query.filter_by(campaign_id=campaign_id).order_by(EmailLog.sent_at.desc()).all()]
        sms_logs = [log.to_dict() for log in SMSLog.query.filter_by(campaign_id=campaign_id).order_by(SMSLog.sent_at.desc()).all()]
        call_logs = [log.to_dict() for log in CallLog.query.filter_by(campaign_id=campaign_id).order_by(CallLog.called_at.desc()).all()]
        
        return jsonify({
            "success": True,
            "campaign": campaign.to_dict(),
            "logs": {
                "emails": email_logs,
                "sms": sms_logs,
                "calls": call_logs
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@analytics_bp.route("/api/conversation/<int:call_log_id>")
@login_required
def get_conversation(call_log_id):
    """Get detailed conversation data for a specific call"""
    try:
        # Get call log and verify it belongs to user's campaign
        call_log = CallLog.query.join(Campaign).filter(
            CallLog.id == call_log_id,
            Campaign.created_by == current_user.id
        ).first()
        
        if not call_log:
            return jsonify({"success": False, "error": "Call log not found"}), 404
        
        return jsonify({
            "success": True,
            "call_log": call_log.to_dict()
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


