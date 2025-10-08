
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import Campaign, db
from database import mysql_conn
from api_services import AIAgentAPI
from datetime import datetime
import json

campaigns_bp = Blueprint("campaigns", __name__)

ai_agent = AIAgentAPI()

@campaigns_bp.route("/api/client-groups")
@login_required
def get_client_groups():
    groups = mysql_conn.get_client_groups()
    return jsonify({"success": True, "groups": groups})

@campaigns_bp.route("/api/clients/<int:group_id>")
@login_required
def get_clients(group_id):
    clients = mysql_conn.get_clients_by_group(group_id)
    return jsonify({"success": True, "clients": clients, "count": len(clients)})

@campaigns_bp.route("/api/campaigns", methods=["GET"])
@login_required
def get_campaigns():
    campaigns = Campaign.query.filter_by(created_by=current_user.id).order_by(Campaign.created_at.desc()).all()
    return jsonify({
        "success": True,
        "campaigns": [c.to_dict() for c in campaigns]
    })

@campaigns_bp.route("/api/campaigns", methods=["POST"])
@login_required
def create_campaign():
    data = request.json

    # Validate groups
    client_group_ids = data.get("client_group_ids")
    if not client_group_ids or not isinstance(client_group_ids, list):
        return jsonify({"success": False, "error": "client_group_ids must be a non-empty list"}), 400
    
    campaign = Campaign(
        name=data.get("name"),
        description=data.get("description"),
        client_group_ids=client_group_ids,  # ✅ store as list (JSON column)
        email_subject=data.get("email_subject"),
        email_body=data.get("email_body"),
        email_attachment_file=data.get("email_attachment_file"),
        email_attachment_url=data.get("email_attachment_url"),
        email_attachment_type=data.get("email_attachment_type"),
        sms_message=data.get("sms_message"),
        voice_file_path=data.get("voice_file_path"),
        ai_agent_profile=data.get("ai_agent_profile"),
        social_config=data.get("social_config"),
        status="draft",
        created_by=current_user.id
    )
    
    db.session.add(campaign)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "campaign": campaign.to_dict()
    })

@campaigns_bp.route("/api/launch-campaign", methods=["POST"])
@login_required
def launch_campaign():
    """Launch campaign with support for multiple client groups and enhanced logging"""
    data = request.json
    campaign_id = data.get("campaign_id")
    
    # Fetch campaign
    campaign = Campaign.query.filter_by(id=campaign_id, created_by=current_user.id).first()
    if not campaign:
        return jsonify({"success": False, "error": "Campaign not found"}), 404
    
    # Load client groups (stored as JSON)
    try:
        client_group_ids = json.loads(campaign.client_group_ids)
    except Exception:
        return jsonify({"success": False, "error": "Invalid client group data"}), 400

    if not isinstance(client_group_ids, list) or not client_group_ids:
        return jsonify({"success": False, "error": "No client groups found in campaign"}), 400

    # Fetch clients from all groups
    all_clients = []
    for group_id in client_group_ids:
        clients = mysql_conn.get_clients_by_group(group_id)
        if clients:
            all_clients.extend(clients)

    if not all_clients:
        return jsonify({
            "success": False,
            "error": "No clients found in the selected groups"
        }), 400

    results = {
        "campaign_id": campaign_id,
        "total_clients": len(all_clients),
        "actions": {}
    }

    # Execute Email Campaign
    if campaign.email_subject and campaign.email_body:
        print(f"Sending emails to {len(all_clients)} clients...")
        email_results = ai_agent.send_email(
            all_clients, 
            campaign.email_subject, 
            campaign.email_body,
            campaign_id,
            campaign.email_attachment_file,
            campaign.email_attachment_type
        )
        results["actions"]["email"] = email_results
        print(f"Email results: {email_results["success"]} success, {email_results["failed"]} failed")

    # Execute SMS Campaign
    if campaign.sms_message:
        print(f"Sending SMS to {len(all_clients)} clients...")
        sms_results = ai_agent.send_sms(
            all_clients, 
            campaign.sms_message,
            campaign_id
        )
        results["actions"]["sms"] = sms_results
        print(f"SMS results: {sms_results["success"]} success, {sms_results["failed"]} failed")

    # Execute Voice Campaign
    if campaign.voice_file_path:
        print(f"Making voice calls to {len(all_clients)} clients...")
        voice_results = ai_agent.leave_voice_message(
            all_clients, 
            campaign.voice_file_path,
            campaign_id
        )
        results["actions"]["voice"] = voice_results
        print(f"Voice results: {voice_results["success"]} success, {voice_results["failed"]} failed")

    # Execute AI Agent Calls
    if campaign.ai_agent_profile:
        print(f"Making AI agent calls to {len(all_clients)} clients...")
        ai_call_results = ai_agent.interactive_call(
            all_clients, 
            campaign.ai_agent_profile,
            campaign_id
        )
        results["actions"]["ai_calls"] = ai_call_results
        print(f"AI call results: {ai_call_results["success"]} success, {ai_call_results["failed"]} failed")

    # Update campaign status
    campaign.status = "launched"
    campaign.launched_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "success": True,
        "results": results
    })


