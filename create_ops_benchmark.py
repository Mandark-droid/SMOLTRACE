#!/usr/bin/env python3
"""
Create APM/AIOps/SRE/DevOps benchmark dataset for evaluating agentic models.

This dataset focuses on real-world operations scenarios:
- Log analysis and troubleshooting
- Metrics interpretation and alerting
- Infrastructure automation
- Incident response and root cause analysis
- Configuration management
- Performance optimization
"""

import os

from datasets import Dataset
from dotenv import load_dotenv

load_dotenv()


def create_ops_benchmark():
    """Create comprehensive operations benchmark dataset."""

    tasks = [
        # ========================================================================
        # Category 1: Log Analysis & Troubleshooting (Easy)
        # ========================================================================
        {
            "id": "ops_log_error_detection",
            "prompt": """You have access to application logs. Search for ERROR level messages in the logs from the last hour and identify the most common error pattern. What is the root cause?

Logs are in: ./logs/app.log
Use file tools to read and analyze the logs.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 3,
            "difficulty": "easy",
            "agent_type": "both",
            "category": "log_analysis",
            "expected_keywords": ["ERROR", "pattern", "cause"],
            "required_tools": ["read_file", "search_files"],
        },
        {
            "id": "ops_log_rate_spike",
            "prompt": """Analyze the application error rate over the past 24 hours. Has there been a significant spike in errors? If yes, at what time and what type of errors increased?

Log directory: ./logs/
Use file and search tools to analyze patterns.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 4,
            "difficulty": "easy",
            "agent_type": "both",
            "category": "log_analysis",
            "expected_keywords": ["spike", "time", "error type"],
            "required_tools": ["list_directory", "read_file", "search_files"],
        },
        # ========================================================================
        # Category 2: Metrics Analysis & Monitoring (Easy to Medium)
        # ========================================================================
        {
            "id": "ops_cpu_threshold_alert",
            "prompt": """Check if the CPU utilization in metrics.json exceeds 80% threshold. If yes, list the timestamps when this occurred and recommend actions.

Metrics file: ./metrics/cpu_metrics.json
Use read_file to access metrics data.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 2,
            "difficulty": "easy",
            "agent_type": "both",
            "category": "metrics_monitoring",
            "expected_keywords": ["80%", "threshold", "recommend"],
            "required_tools": ["read_file", "python_interpreter"],
        },
        {
            "id": "ops_memory_leak_detection",
            "prompt": """Analyze the memory usage trend in memory_metrics.json over the past 7 days. Is there a memory leak? Calculate the rate of memory growth and estimate when memory will be exhausted.

File: ./metrics/memory_metrics.json
Use Python for calculations if needed.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 3,
            "difficulty": "medium",
            "agent_type": "both",
            "category": "metrics_monitoring",
            "expected_keywords": ["leak", "growth rate", "exhausted"],
            "required_tools": ["read_file", "python_interpreter"],
        },
        {
            "id": "ops_disk_space_projection",
            "prompt": """Based on the disk usage data in disk_metrics.json, project when the disk will reach 90% capacity. Current usage trends show growth over the past 30 days.

File: ./metrics/disk_metrics.json
Calculate the growth trend and make a projection.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 2,
            "difficulty": "medium",
            "agent_type": "both",
            "category": "metrics_monitoring",
            "expected_keywords": ["90%", "projection", "days"],
            "required_tools": ["read_file", "python_interpreter"],
        },
        # ========================================================================
        # Category 3: Configuration Management (Medium)
        # ========================================================================
        {
            "id": "ops_config_validation",
            "prompt": """Validate the Kubernetes deployment configuration in k8s/deployment.yaml. Check for:
1. Resource limits are set
2. Health checks are configured
3. Replicas >= 2 for high availability

Report any missing configurations.

File: ./k8s/deployment.yaml""",
            "expected_tool": "multiple",
            "expected_tool_calls": 2,
            "difficulty": "medium",
            "agent_type": "both",
            "category": "configuration",
            "expected_keywords": ["resource limits", "health checks", "replicas"],
            "required_tools": ["read_file"],
        },
        {
            "id": "ops_env_var_mismatch",
            "prompt": """Compare environment variables between .env.production and .env.staging files. Identify any mismatches that could cause production issues.

Files: ./config/.env.production, ./config/.env.staging""",
            "expected_tool": "multiple",
            "expected_tool_calls": 3,
            "difficulty": "medium",
            "agent_type": "both",
            "category": "configuration",
            "expected_keywords": ["mismatch", "difference", "production"],
            "required_tools": ["read_file"],
        },
        {
            "id": "ops_nginx_config_syntax",
            "prompt": """Check the Nginx configuration file for syntax errors and security issues. Look for:
1. Missing SSL configuration
2. Incorrect proxy settings
3. Security headers

File: ./config/nginx.conf""",
            "expected_tool": "multiple",
            "expected_tool_calls": 2,
            "difficulty": "medium",
            "agent_type": "both",
            "category": "configuration",
            "expected_keywords": ["SSL", "security", "proxy"],
            "required_tools": ["read_file"],
        },
        # ========================================================================
        # Category 4: Incident Response & Root Cause Analysis (Hard)
        # ========================================================================
        {
            "id": "ops_503_error_diagnosis",
            "prompt": """The application is returning 503 errors. Investigate:
1. Check application logs in ./logs/app.log
2. Check system metrics in ./metrics/
3. Review recent deployments in ./deployments/history.json
4. Identify the root cause and recommended fix

Use multiple file operations to gather evidence.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 5,
            "difficulty": "hard",
            "agent_type": "both",
            "category": "incident_response",
            "expected_keywords": ["root cause", "503", "fix"],
            "required_tools": ["read_file", "search_files", "list_directory"],
        },
        {
            "id": "ops_db_connection_pool_exhaustion",
            "prompt": """Database connection pool is exhausted causing application timeouts. Analyze:
1. Connection pool configuration in ./config/database.yml
2. Connection metrics in ./metrics/db_connections.json
3. Application logs in ./logs/app.log
4. Identify why connections are not being released and suggest configuration changes

This requires analyzing multiple data sources.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 5,
            "difficulty": "hard",
            "agent_type": "both",
            "category": "incident_response",
            "expected_keywords": ["connection pool", "timeout", "configuration"],
            "required_tools": ["read_file", "search_files"],
        },
        {
            "id": "ops_cascade_failure_analysis",
            "prompt": """A cascade failure occurred at 14:30 UTC. Reconstruct the timeline:
1. Initial service failure from logs (./logs/service-*.log)
2. Propagation to dependent services
3. Load balancer behavior (./logs/lb.log)
4. Recovery actions taken
5. Provide a complete incident timeline and recommendations

Use file search to find relevant log entries across multiple services.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 6,
            "difficulty": "hard",
            "agent_type": "both",
            "category": "incident_response",
            "expected_keywords": ["timeline", "cascade", "14:30", "recommendations"],
            "required_tools": ["search_files", "read_file", "list_directory"],
        },
        # ========================================================================
        # Category 5: Performance Optimization (Medium to Hard)
        # ========================================================================
        {
            "id": "ops_slow_query_identification",
            "prompt": """Analyze the database slow query log and identify:
1. Top 3 slowest queries
2. Tables involved
3. Suggested indexes to improve performance

File: ./logs/mysql-slow.log
Use search and analysis tools.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 3,
            "difficulty": "medium",
            "agent_type": "both",
            "category": "performance",
            "expected_keywords": ["slow", "queries", "indexes"],
            "required_tools": ["read_file", "search_files"],
        },
        {
            "id": "ops_api_latency_optimization",
            "prompt": """API response times have increased by 200% in the past week. Analyze:
1. API latency metrics in ./metrics/api_latency.json
2. Database query times in ./metrics/db_query_times.json
3. External service dependencies in ./config/services.yml
4. Identify the bottleneck and optimization strategy

Requires multi-source analysis and Python calculations.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 5,
            "difficulty": "hard",
            "agent_type": "both",
            "category": "performance",
            "expected_keywords": ["bottleneck", "latency", "optimization"],
            "required_tools": ["read_file", "python_interpreter"],
        },
        {
            "id": "ops_cache_hit_rate_analysis",
            "prompt": """Cache hit rate has dropped from 95% to 60% over 3 days. Investigate:
1. Cache configuration in ./config/redis.conf
2. Cache metrics in ./metrics/cache_stats.json
3. Application code changes in ./deployments/changelog.txt
4. Determine why cache effectiveness decreased

Analyze multiple sources to find correlation.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 4,
            "difficulty": "hard",
            "agent_type": "both",
            "category": "performance",
            "expected_keywords": ["cache", "hit rate", "60%", "cause"],
            "required_tools": ["read_file", "search_files"],
        },
        # ========================================================================
        # Category 6: Infrastructure Automation (Medium)
        # ========================================================================
        {
            "id": "ops_scaling_decision",
            "prompt": """Based on traffic patterns in ./metrics/traffic.json over the past 7 days, should we scale up the infrastructure? Calculate:
1. Average requests per second
2. Peak load times
3. Current capacity utilization
4. Scaling recommendation (yes/no and by how many instances)

Use Python for calculations.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 3,
            "difficulty": "medium",
            "agent_type": "both",
            "category": "automation",
            "expected_keywords": ["scale", "capacity", "instances"],
            "required_tools": ["read_file", "python_interpreter"],
        },
        {
            "id": "ops_backup_verification",
            "prompt": """Verify that all critical databases have recent backups. Check:
1. Backup manifest in ./backups/manifest.json
2. Last backup timestamp for each database
3. Backup size trends
4. Alert if any backup is older than 24 hours

File operations and time calculations required.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 2,
            "difficulty": "medium",
            "agent_type": "both",
            "category": "automation",
            "expected_keywords": ["backup", "24 hours", "alert"],
            "required_tools": ["read_file", "python_interpreter"],
        },
        {
            "id": "ops_certificate_expiry",
            "prompt": """Check SSL certificate expiration dates in ./config/certificates.json. List all certificates expiring within 30 days and prioritize by criticality.

Calculate days until expiry for each certificate.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 2,
            "difficulty": "easy",
            "agent_type": "both",
            "category": "automation",
            "expected_keywords": ["certificate", "30 days", "expiry"],
            "required_tools": ["read_file", "python_interpreter"],
        },
        # ========================================================================
        # Category 7: Security & Compliance (Medium to Hard)
        # ========================================================================
        {
            "id": "ops_security_scan_results",
            "prompt": """Review the security scan results in ./security/scan_results.json. Identify:
1. Critical vulnerabilities (CVSS >= 8.0)
2. Affected services
3. Available patches
4. Prioritized remediation plan

Analyze and categorize security issues.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 2,
            "difficulty": "medium",
            "agent_type": "both",
            "category": "security",
            "expected_keywords": ["critical", "CVSS", "remediation"],
            "required_tools": ["read_file", "python_interpreter"],
        },
        {
            "id": "ops_access_log_anomaly",
            "prompt": """Detect anomalous access patterns in ./logs/access.log that might indicate a security breach:
1. Unusual IP addresses
2. Failed authentication attempts
3. Access to sensitive endpoints
4. Time-based patterns (off-hours access)

Search and analyze access logs for suspicious activity.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 4,
            "difficulty": "hard",
            "agent_type": "both",
            "category": "security",
            "expected_keywords": ["anomaly", "suspicious", "breach"],
            "required_tools": ["read_file", "search_files", "python_interpreter"],
        },
        {
            "id": "ops_compliance_audit",
            "prompt": """Perform a compliance audit for PCI-DSS requirements. Check:
1. Encryption settings in ./config/encryption.yml
2. Access control policies in ./config/iam_policies.json
3. Audit logging configuration in ./config/audit.conf
4. Generate compliance report with pass/fail for each requirement

Files in ./config/ directory.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 4,
            "difficulty": "hard",
            "agent_type": "both",
            "category": "security",
            "expected_keywords": ["compliance", "PCI-DSS", "audit"],
            "required_tools": ["read_file", "list_directory"],
        },
        # ========================================================================
        # Category 8: Multi-Service Debugging (Hard)
        # ========================================================================
        {
            "id": "ops_microservice_trace_analysis",
            "prompt": """A user request is experiencing 10-second latency. Trace through the microservices:
1. API Gateway logs: ./logs/gateway.log
2. Auth Service logs: ./logs/auth.log
3. User Service logs: ./logs/user-service.log
4. Database logs: ./logs/postgres.log
5. Identify which service is the bottleneck and why

Request ID: req-abc-123
Search across multiple log files.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 6,
            "difficulty": "hard",
            "agent_type": "both",
            "category": "debugging",
            "expected_keywords": ["req-abc-123", "bottleneck", "latency"],
            "required_tools": ["search_files", "read_file"],
        },
        {
            "id": "ops_distributed_transaction_failure",
            "prompt": """A distributed transaction failed across multiple services. Reconstruct what happened:
1. Transaction ID: txn-789-xyz
2. Check transaction logs in ./logs/transactions/
3. Check service states in ./state/
4. Determine which service failed first and why compensation didn't work

Use directory listing and file search.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 5,
            "difficulty": "hard",
            "agent_type": "both",
            "category": "debugging",
            "expected_keywords": ["txn-789-xyz", "failed", "compensation"],
            "required_tools": ["list_directory", "search_files", "read_file"],
        },
        # ========================================================================
        # Category 9: Cost Optimization (Medium)
        # ========================================================================
        {
            "id": "ops_cloud_cost_analysis",
            "prompt": """Analyze cloud spending data in ./billing/aws_costs.json for the past month:
1. Identify top 3 cost drivers
2. Find resources with <20% utilization
3. Calculate potential savings from rightsizing
4. Recommend specific optimizations

Use Python for calculations.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 3,
            "difficulty": "medium",
            "agent_type": "both",
            "category": "cost_optimization",
            "expected_keywords": ["cost", "savings", "rightsizing"],
            "required_tools": ["read_file", "python_interpreter"],
        },
        {
            "id": "ops_storage_cleanup",
            "prompt": """Review storage usage across environments in ./storage/inventory.json:
1. Identify old snapshots (>90 days)
2. Find unused volumes
3. Calculate storage costs
4. Provide cleanup recommendations

Analyze storage data and calculate costs.""",
            "expected_tool": "multiple",
            "expected_tool_calls": 2,
            "difficulty": "medium",
            "agent_type": "both",
            "category": "cost_optimization",
            "expected_keywords": ["snapshot", "cleanup", "cost"],
            "required_tools": ["read_file", "python_interpreter"],
        },
    ]

    print(f"Created {len(tasks)} operations benchmark tasks")
    print("\nBreakdown by category:")
    categories = {}
    for task in tasks:
        cat = task["category"]
        categories[cat] = categories.get(cat, 0) + 1
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")

    print("\nBreakdown by difficulty:")
    difficulties = {}
    for task in tasks:
        diff = task["difficulty"]
        difficulties[diff] = difficulties.get(diff, 0) + 1
    for diff, count in sorted(difficulties.items()):
        print(f"  {diff}: {count}")

    return tasks


def push_to_hub(tasks):
    """Push dataset to HuggingFace Hub."""
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("[ERROR] HF_TOKEN not set")
        return False

    print("\nCreating dataset...")
    dataset = Dataset.from_list(tasks)

    dataset_name = "kshitijthakkar/smoltrace-ops-benchmark"
    print(f"\nPushing to {dataset_name}...")

    try:
        dataset.push_to_hub(dataset_name, token=hf_token, private=False)
        print(f"[SUCCESS] Dataset pushed to https://huggingface.co/datasets/{dataset_name}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to push: {e}")
        return False


if __name__ == "__main__":
    print("=" * 80)
    print("Creating APM/AIOps/SRE/DevOps Benchmark Dataset")
    print("=" * 80)

    tasks = create_ops_benchmark()
    push_to_hub(tasks)

    print("\n" + "=" * 80)
    print("Dataset Creation Complete!")
    print("=" * 80)
