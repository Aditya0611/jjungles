"""
Admin API for Managing Scheduler Settings

This module provides a simple REST API for admins to manage scraper
scheduling settings (frequency, enable/disable platforms).

Usage:
    # Start admin API server
    python admin_api.py

    # Or with custom port
    ADMIN_API_PORT=8080 python admin_api.py
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Import Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.error("Supabase not available. Install with: pip install supabase flask flask-cors")


# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
ADMIN_API_PORT = int(os.environ.get("ADMIN_API_PORT", "5000"))
ADMIN_API_HOST = os.environ.get("ADMIN_API_HOST", "0.0.0.0")
ADMIN_API_ENABLED = os.environ.get("ADMIN_API_ENABLED", "true").lower() == "true"
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

# Allowed platforms for validation
ALLOWED_PLATFORMS = ["tiktok", "instagram", "x", "linkedin", "facebook"]

# Initialize Flask app
app = Flask(__name__)
# Enable CORS with restricted origins
CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}})

# Initialize Supabase client
supabase: Optional[Client] = None

if SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {e}")
else:
    logger.warning("Supabase not configured, admin API will have limited functionality")

def validate_platform(platform: str) -> bool:
    """Validate platform name."""
    return platform.lower() in ALLOWED_PLATFORMS


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "supabase_available": supabase is not None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cors_origins": CORS_ORIGINS
    })


@app.route("/api/run-history", methods=["GET"])
def get_run_history():
    """Get run history.
    
    Query Parameters:
        platform: Filter by platform (optional)
        limit: Number of records to return (default: 50, max: 500)
        status: Filter by status (optional: running, completed, failed, cancelled)
        days: Number of days to look back (default: 7)
    
    Returns:
        JSON array of run history records
    """
    if not supabase:
        return jsonify({"error": "Supabase not available"}), 500
    
    try:
        platform = request.args.get("platform")
        limit = min(int(request.args.get("limit", 50)), 500)
        status = request.args.get("status")
        days = int(request.args.get("days", 7))
        
        query = supabase.table("run_history").select("*")
        
        if platform:
            if not validate_platform(platform):
                 return jsonify({"error": "Invalid platform"}), 400
            # Sanitize input to prevent injection (though Supabase handles this, extra layer is safe)
            import re
            if not re.match(r'^[a-z0-9_]+$', platform.lower()):
                return jsonify({"error": "Invalid platform format"}), 400
            query = query.eq("platform", platform.lower())
        
        if status:
            query = query.eq("status", status)
        
        # Filter by date
        from datetime import timedelta
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        query = query.gte("started_at", cutoff_date)
        
        # Order and limit
        query = query.order("started_at", desc=True).limit(limit)
        
        result = query.execute()
        return jsonify(result.data)
        
    except Exception as e:
        logger.error(f"Error getting run history: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/run-history/<int:run_id>", methods=["GET"])
def get_run_history_item(run_id: int):
    """Get a specific run history record.
    
    Args:
        run_id: Run history ID
    
    Returns:
        JSON object with run history details
    """
    if not supabase:
        return jsonify({"error": "Supabase not available"}), 500
    
    try:
        result = supabase.table("run_history").select("*").eq("id", run_id).execute()
        
        if result.data:
            return jsonify(result.data[0])
        else:
            return jsonify({"error": f"Run history {run_id} not found"}), 404
            
    except Exception as e:
        logger.error(f"Error getting run history {run_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/run-history/stats", methods=["GET"])
def get_run_history_stats():
    """Get run history statistics.
    
    Query Parameters:
        platform: Filter by platform (optional)
        days: Number of days to analyze (default: 7)
    
    Returns:
        JSON object with statistics
    """
    if not supabase:
        return jsonify({"error": "Supabase not available"}), 500
    
    try:
        platform = request.args.get("platform")
        days = int(request.args.get("days", 7))
        
        # Use database function if available
        try:
            result = supabase.rpc("get_run_statistics", {
                "p_platform": platform.lower() if platform else None,
                "p_days": days
            }).execute()
            return jsonify(result.data)
        except:
            # Fallback to manual query
            query = supabase.table("run_history").select("*")
            
            if platform:
                if not validate_platform(platform):
                     return jsonify({"error": "Invalid platform"}), 400
                query = query.eq("platform", platform.lower())
            
            from datetime import timedelta
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            query = query.gte("started_at", cutoff_date)
            
            result = query.execute()
            
            # Calculate statistics
            stats = {
                "total_runs": len(result.data),
                "successful_runs": sum(1 for r in result.data if r.get("status") == "completed"),
                "failed_runs": sum(1 for r in result.data if r.get("status") == "failed"),
                "running_runs": sum(1 for r in result.data if r.get("status") == "running"),
                "avg_duration_seconds": sum(r.get("duration_seconds", 0) for r in result.data if r.get("duration_seconds")) / max(len([r for r in result.data if r.get("duration_seconds")]), 1),
                "avg_records_scraped": sum(r.get("records_scraped", 0) for r in result.data) / max(len(result.data), 1)
            }
            
            return jsonify(stats)
            
    except Exception as e:
        logger.error(f"Error getting run history stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Get all scheduler settings.
    
    Returns:
        JSON array of platform settings
    """
    if not supabase:
        return jsonify({"error": "Supabase not available"}), 500
    
    try:
        result = supabase.table("scheduler_settings").select("*").order("platform").execute()
        return jsonify(result.data)
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings/<platform>", methods=["GET"])
def get_setting(platform: str):
    """Get settings for a specific platform.
    
    Args:
        platform: Platform name (tiktok, instagram, x, linkedin, facebook)
    
    Returns:
        JSON object with platform settings
    """
    if not supabase:
        return jsonify({"error": "Supabase not available"}), 500
    
    if not validate_platform(platform):
        return jsonify({"error": "Invalid platform"}), 400
    

    try:
        result = supabase.table("scheduler_settings").select("*").eq("platform", platform.lower()).execute()
        if result.data:
            return jsonify(result.data[0])
        else:
            return jsonify({"error": f"Platform '{platform}' not found"}), 404
    except Exception as e:
        logger.error(f"Error getting setting for {platform}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings/<platform>", methods=["PUT"])
def update_setting(platform: str):
    """Update settings for a specific platform.
    
    Args:
        platform: Platform name (tiktok, instagram, x, linkedin, facebook)
    
    Request Body (JSON):
        {
            "enabled": true/false,
            "frequency_hours": 2.0-4.0,
            "metadata": {...}  # Optional
        }
    
    Returns:
        Updated settings object
    """
    if not supabase:
        return jsonify({"error": "Supabase not available"}), 500
    
    if not validate_platform(platform):
        return jsonify({"error": "Invalid platform"}), 400
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate frequency_hours
        if "frequency_hours" in data:
            freq = float(data["frequency_hours"])
            if freq < 0.5 or freq > 24.0:
                return jsonify({"error": "frequency_hours must be between 0.5 and 24.0"}), 400
        
        # Update settings
        update_data = {}
        if "enabled" in data:
            update_data["enabled"] = bool(data["enabled"])
        if "frequency_hours" in data:
            update_data["frequency_hours"] = float(data["frequency_hours"])
        if "metadata" in data:
            update_data["metadata"] = data["metadata"]
        
        result = supabase.table("scheduler_settings").update(update_data).eq("platform", platform.lower()).execute()
        
        if result.data:
            logger.info(f"Updated settings for {platform}: {update_data}")
            return jsonify(result.data[0])
        else:
            return jsonify({"error": f"Platform '{platform}' not found"}), 404
            
    except Exception as e:
        logger.error(f"Error updating setting for {platform}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings/<platform>/frequency", methods=["PUT"])
def update_frequency(platform: str):
    """Update frequency for a platform (convenience endpoint).
    
    Args:
        platform: Platform name
    
    Request Body (JSON):
        {
            "frequency_hours": 2.0-4.0
        }
    
    Returns:
        Updated settings object
    """
    if not supabase:
        return jsonify({"error": "Supabase not available"}), 500
    
    if not validate_platform(platform):
        return jsonify({"error": "Invalid platform"}), 400
    
    try:
        data = request.get_json()
        if not data or "frequency_hours" not in data:
            return jsonify({"error": "frequency_hours required"}), 400
        
        freq = float(data["frequency_hours"])
        if freq < 0.5 or freq > 24.0:
            return jsonify({"error": "frequency_hours must be between 0.5 and 24.0"}), 400
        
        result = supabase.table("scheduler_settings").update({
            "frequency_hours": freq
        }).eq("platform", platform.lower()).execute()
        
        if result.data:
            logger.info(f"Updated frequency for {platform} to {freq} hours")
            return jsonify(result.data[0])
        else:
            return jsonify({"error": f"Platform '{platform}' not found"}), 404
            
    except Exception as e:
        logger.error(f"Error updating frequency for {platform}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings/<platform>/enable", methods=["POST"])
def enable_platform(platform: str):
    """Enable a platform.
    
    Args:
        platform: Platform name
    
    Returns:
        Updated settings object
    """
    if not supabase:
        return jsonify({"error": "Supabase not available"}), 500
    
    if not validate_platform(platform):
        return jsonify({"error": "Invalid platform"}), 400
    
    try:
        result = supabase.table("scheduler_settings").update({
            "enabled": True
        }).eq("platform", platform.lower()).execute()
        
        if result.data:
            logger.info(f"Enabled platform: {platform}")
            return jsonify(result.data[0])
        else:
            return jsonify({"error": f"Platform '{platform}' not found"}), 404
            
    except Exception as e:
        logger.error(f"Error enabling platform {platform}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings/<platform>/disable", methods=["POST"])
def disable_platform(platform: str):
    """Disable a platform.
    
    Args:
        platform: Platform name
    
    Returns:
        Updated settings object
    """
    if not supabase:
        return jsonify({"error": "Supabase not available"}), 500
    
    if not validate_platform(platform):
        return jsonify({"error": "Invalid platform"}), 400
    
    try:
        result = supabase.table("scheduler_settings").update({
            "enabled": False
        }).eq("platform", platform.lower()).execute()
        
        if result.data:
            logger.info(f"Disabled platform: {platform}")
            return jsonify(result.data[0])
        else:
            return jsonify({"error": f"Platform '{platform}' not found"}), 404
            
    except Exception as e:
        logger.error(f"Error disabling platform {platform}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get scheduler statistics.
    
    Returns:
        JSON object with statistics
    """
    if not supabase:
        return jsonify({"error": "Supabase not available"}), 500
    
    try:
        result = supabase.table("scheduler_settings").select("*").execute()
        
        stats = {
            "total_platforms": len(result.data),
            "enabled_platforms": sum(1 for r in result.data if r.get("enabled")),
            "total_runs": sum(r.get("run_count", 0) for r in result.data),
            "total_successes": sum(r.get("success_count", 0) for r in result.data),
            "total_failures": sum(r.get("failure_count", 0) for r in result.data),
            "platforms": []
        }
        
        for row in result.data:
            stats["platforms"].append({
                "platform": row.get("platform"),
                "enabled": row.get("enabled"),
                "frequency_hours": row.get("frequency_hours"),
                "run_count": row.get("run_count", 0),
                "success_count": row.get("success_count", 0),
                "failure_count": row.get("failure_count", 0),
                "last_run_at": row.get("last_run_at"),
                "next_run_at": row.get("next_run_at")
            })
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500


def main():
    """Start admin API server."""
    if not ADMIN_API_ENABLED:
        logger.warning("Admin API is disabled (ADMIN_API_ENABLED=false)")
        return
    
    logger.info("="*60)
    logger.info("ADMIN API STARTING")
    logger.info("="*60)
    logger.info(f"Host: {ADMIN_API_HOST}")
    logger.info(f"Port: {ADMIN_API_PORT}")
    logger.info(f"Supabase available: {supabase is not None}")
    logger.info("="*60)
    
    app.run(host=ADMIN_API_HOST, port=ADMIN_API_PORT, debug=False)


if __name__ == "__main__":
    main()

