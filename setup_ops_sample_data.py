#!/usr/bin/env python3
"""
Setup sample data for smoltrace-ops-benchmark evaluation.

Creates realistic sample files and directories that the ops benchmark tasks expect.
This data serves as the working directory for agent evaluations.
"""

import json
from datetime import datetime
from pathlib import Path


def setup_ops_sample_data(base_dir="ops_sample"):
    """Create comprehensive sample data structure for ops benchmark.

    Args:
        base_dir: Directory name for sample data (default: ops_sample)
    """

    base_path = Path(base_dir)

    # Create fresh directory
    if base_path.exists():
        print(f"Directory {base_path} already exists. Using existing directory.")
    else:
        base_path.mkdir(exist_ok=True)
        print(f"Created directory: {base_path}")

    print(f"\nSetting up ops benchmark sample data in: {base_path.absolute()}")

    # ========================================================================
    # 1. Logs Directory
    # ========================================================================
    logs_dir = base_path / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Application logs
    (logs_dir / "app.log").write_text(
        """2024-11-01 10:15:23 INFO  Application started successfully
2024-11-01 10:16:45 INFO  Connected to database
2024-11-01 10:17:12 ERROR Database connection timeout after 30s
2024-11-01 10:17:15 ERROR Database connection timeout after 30s
2024-11-01 10:18:03 WARN  Retrying database connection (attempt 1/3)
2024-11-01 10:18:35 ERROR Database connection timeout after 30s
2024-11-01 10:19:02 INFO  Successfully reconnected to database
2024-11-01 10:20:15 INFO  Processing request from user_12345
2024-11-01 10:21:30 ERROR NullPointerException in OrderService.processOrder() line 245
2024-11-01 10:22:45 ERROR NullPointerException in OrderService.processOrder() line 245
2024-11-01 10:23:10 WARN  High memory usage: 85%
2024-11-01 10:24:00 ERROR NullPointerException in OrderService.processOrder() line 245
2024-11-01 10:25:15 INFO  Request completed successfully
"""
    )

    # Service logs
    for service in ["auth", "user-service", "gateway", "postgres"]:
        (logs_dir / f"{service}.log").write_text(
            f"""2024-11-01 10:15:00 INFO  [{service.upper()}] Service starting
2024-11-01 10:15:05 INFO  [{service.upper()}] Service ready
2024-11-01 10:16:00 INFO  [{service.upper()}] Processing requests
2024-11-01 10:17:30 WARN  [{service.upper()}] High latency detected: 2500ms
2024-11-01 10:18:00 INFO  [{service.upper()}] Normal operations resumed
"""
        )

    # Load balancer logs
    (logs_dir / "lb.log").write_text(
        """2024-11-01 10:15:00 INFO  Load balancer started
2024-11-01 10:16:00 INFO  Backend server 10.0.1.10:8080 healthy
2024-11-01 10:16:00 INFO  Backend server 10.0.1.11:8080 healthy
2024-11-01 10:17:00 WARN  Backend server 10.0.1.10:8080 response time: 3000ms
2024-11-01 10:18:00 ERROR Backend server 10.0.1.10:8080 health check failed
2024-11-01 10:18:05 INFO  Removed 10.0.1.10:8080 from rotation
"""
    )

    # MySQL slow query log
    (logs_dir / "mysql-slow.log").write_text(
        """# Time: 2024-11-01T10:15:00.123456Z
# User@Host: app_user[app_user] @ localhost []
# Query_time: 15.234567  Lock_time: 0.000123 Rows_sent: 1000000  Rows_examined: 5000000
SET timestamp=1698835500;
SELECT * FROM orders o
LEFT JOIN order_items oi ON o.id = oi.order_id
LEFT JOIN products p ON oi.product_id = p.id
WHERE o.created_at > '2024-01-01'
ORDER BY o.created_at DESC;

# Time: 2024-11-01T10:20:00.123456Z
# User@Host: app_user[app_user] @ localhost []
# Query_time: 8.456789  Lock_time: 2.345678 Rows_sent: 500000  Rows_examined: 2500000
SET timestamp=1698835800;
SELECT COUNT(*) FROM users u
JOIN sessions s ON u.id = s.user_id
WHERE s.created_at > NOW() - INTERVAL 30 DAY;
"""
    )

    # Access logs
    (logs_dir / "access.log").write_text(
        """192.168.1.100 - - [01/Nov/2024:10:15:00 +0000] "GET /api/users HTTP/1.1" 200 1234
192.168.1.101 - - [01/Nov/2024:10:15:05 +0000] "POST /api/orders HTTP/1.1" 201 567
192.168.1.102 - - [01/Nov/2024:10:15:10 +0000] "GET /api/products HTTP/1.1" 200 8901
45.142.120.45 - - [01/Nov/2024:10:15:15 +0000] "GET /admin/users HTTP/1.1" 403 89
45.142.120.45 - - [01/Nov/2024:10:15:16 +0000] "GET /admin/config HTTP/1.1" 403 89
45.142.120.45 - - [01/Nov/2024:10:15:17 +0000] "POST /admin/users HTTP/1.1" 403 89
45.142.120.45 - - [01/Nov/2024:10:15:18 +0000] "GET /../../../etc/passwd HTTP/1.1" 400 45
"""
    )

    # Transaction logs directory
    transactions_dir = logs_dir / "transactions"
    transactions_dir.mkdir(exist_ok=True)
    (transactions_dir / "2024-11-01.log").write_text(
        """2024-11-01 10:15:00 TXN_START transaction_id=txn_12345
2024-11-01 10:15:01 TXN_STEP transaction_id=txn_12345 action=debit account=ACC001 amount=100.00
2024-11-01 10:15:02 TXN_STEP transaction_id=txn_12345 action=credit account=ACC002 amount=100.00
2024-11-01 10:15:03 TXN_COMMIT transaction_id=txn_12345 status=SUCCESS
"""
    )

    print("✓ Created logs directory with sample log files")

    # ========================================================================
    # 2. Metrics Directory
    # ========================================================================
    metrics_dir = base_path / "metrics"
    metrics_dir.mkdir(exist_ok=True)

    # CPU metrics
    cpu_metrics = {
        "metric_name": "cpu_utilization",
        "timestamp": datetime.now().isoformat(),
        "data_points": [
            {"time": "10:00", "value": 45.2, "host": "web-01"},
            {"time": "10:05", "value": 52.1, "host": "web-01"},
            {"time": "10:10", "value": 78.5, "host": "web-01"},
            {"time": "10:15", "value": 89.3, "host": "web-01"},
            {"time": "10:20", "value": 92.1, "host": "web-01"},
            {"time": "10:25", "value": 55.4, "host": "web-01"},
        ],
        "threshold": 85.0,
        "alert_status": "CRITICAL",
    }
    (metrics_dir / "cpu_metrics.json").write_text(json.dumps(cpu_metrics, indent=2))

    # Memory metrics
    memory_metrics = {
        "metric_name": "memory_usage",
        "timestamp": datetime.now().isoformat(),
        "total_gb": 32,
        "used_gb": 28.5,
        "available_gb": 3.5,
        "percent": 89.0,
        "threshold": 80.0,
        "alert_status": "WARNING",
        "processes": [
            {"name": "java", "memory_mb": 8192, "pid": 1234},
            {"name": "postgres", "memory_mb": 4096, "pid": 5678},
            {"name": "redis", "memory_mb": 2048, "pid": 9012},
        ],
    }
    (metrics_dir / "memory_metrics.json").write_text(json.dumps(memory_metrics, indent=2))

    # Disk metrics
    disk_metrics = {
        "metric_name": "disk_usage",
        "timestamp": datetime.now().isoformat(),
        "filesystems": [
            {
                "mount": "/",
                "total_gb": 500,
                "used_gb": 475,
                "available_gb": 25,
                "percent": 95.0,
                "alert_status": "CRITICAL",
            },
            {
                "mount": "/data",
                "total_gb": 2000,
                "used_gb": 1200,
                "available_gb": 800,
                "percent": 60.0,
                "alert_status": "OK",
            },
        ],
        "threshold": 90.0,
    }
    (metrics_dir / "disk_metrics.json").write_text(json.dumps(disk_metrics, indent=2))

    # Database connection metrics
    db_metrics = {
        "metric_name": "database_connections",
        "timestamp": datetime.now().isoformat(),
        "max_connections": 200,
        "active_connections": 195,
        "idle_connections": 150,
        "waiting_connections": 25,
        "connection_pool_exhaustion_count": 15,
        "alert_status": "CRITICAL",
    }
    (metrics_dir / "db_connections.json").write_text(json.dumps(db_metrics, indent=2))

    # API latency metrics
    api_latency = {
        "metric_name": "api_latency",
        "timestamp": datetime.now().isoformat(),
        "endpoints": [
            {
                "path": "/api/users",
                "p50_ms": 45,
                "p95_ms": 120,
                "p99_ms": 250,
                "avg_ms": 65,
                "requests_per_min": 1200,
            },
            {
                "path": "/api/orders",
                "p50_ms": 180,
                "p95_ms": 850,
                "p99_ms": 2500,
                "avg_ms": 320,
                "requests_per_min": 450,
            },
        ],
        "sla_target_ms": 500,
    }
    (metrics_dir / "api_latency.json").write_text(json.dumps(api_latency, indent=2))

    # Database query times
    db_query_times = {
        "metric_name": "database_query_times",
        "timestamp": datetime.now().isoformat(),
        "slow_queries": [
            {
                "query": "SELECT * FROM orders WHERE created_at > ?",
                "avg_time_ms": 1500,
                "count": 45,
                "table": "orders",
            },
            {
                "query": "SELECT COUNT(*) FROM users JOIN sessions",
                "avg_time_ms": 850,
                "count": 120,
                "table": "users",
            },
        ],
        "threshold_ms": 100,
    }
    (metrics_dir / "db_query_times.json").write_text(json.dumps(db_query_times, indent=2))

    # Cache statistics
    cache_stats = {
        "metric_name": "cache_statistics",
        "timestamp": datetime.now().isoformat(),
        "cache_type": "redis",
        "hit_rate": 45.2,
        "miss_rate": 54.8,
        "total_requests": 100000,
        "hits": 45200,
        "misses": 54800,
        "memory_used_mb": 2048,
        "memory_max_mb": 4096,
        "evictions": 1250,
        "target_hit_rate": 95.0,
        "alert_status": "CRITICAL",
    }
    (metrics_dir / "cache_stats.json").write_text(json.dumps(cache_stats, indent=2))

    # Traffic metrics
    traffic_metrics = {
        "metric_name": "traffic_patterns",
        "timestamp": datetime.now().isoformat(),
        "daily_patterns": [
            {"day": "2024-10-25", "requests": 1200000, "peak_rps": 450},
            {"day": "2024-10-26", "requests": 1350000, "peak_rps": 520},
            {"day": "2024-10-27", "requests": 1250000, "peak_rps": 480},
            {"day": "2024-10-28", "requests": 2100000, "peak_rps": 850},
            {"day": "2024-10-29", "requests": 2250000, "peak_rps": 920},
            {"day": "2024-10-30", "requests": 2180000, "peak_rps": 890},
            {"day": "2024-10-31", "requests": 2300000, "peak_rps": 950},
        ],
        "average_rps": 520,
        "growth_rate_percent": 42.5,
    }
    (metrics_dir / "traffic.json").write_text(json.dumps(traffic_metrics, indent=2))

    print("✓ Created metrics directory with sample metric files")

    # ========================================================================
    # 3. Kubernetes Directory
    # ========================================================================
    k8s_dir = base_path / "k8s"
    k8s_dir.mkdir(exist_ok=True)

    deployment_yaml = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: app
        image: myapp:v1.2.3
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "256Mi"
            cpu: "500m"
          limits:
            memory: "512Mi"
            cpu: "1000m"
        env:
        - name: DB_HOST
          value: "postgres.default.svc.cluster.local"
        - name: CACHE_HOST
          value: "redis.default.svc.cluster.local"
"""
    (k8s_dir / "deployment.yaml").write_text(deployment_yaml)

    print("✓ Created k8s directory with deployment configuration")

    # ========================================================================
    # 4. Config Directory
    # ========================================================================
    config_dir = base_path / "config"
    config_dir.mkdir(exist_ok=True)

    # Environment files
    (config_dir / ".env.production").write_text(
        """DB_HOST=prod-db.example.com
DB_PORT=5432
DB_NAME=production_db
DB_USER=prod_user
API_KEY=prod_key_12345
REDIS_HOST=prod-redis.example.com
"""
    )

    (config_dir / ".env.staging").write_text(
        """DB_HOST=staging-db.example.com
DB_PORT=5432
DB_NAME=staging_db
DB_USER=staging_user
API_KEY=staging_key_67890
REDIS_HOST=staging-redis.example.com
"""
    )

    # Nginx configuration
    (config_dir / "nginx.conf").write_text(
        """worker_processes auto;
error_log /var/log/nginx/error.log warn;

events {
    worker_connections 1024;
}

http {
    upstream backend {
        server 10.0.1.10:8080;
        server 10.0.1.11:8080;
        server 10.0.1.12:8080;
    }

    server {
        listen 80;
        server_name api.example.com;

        location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
"""
    )

    # Database configuration
    (config_dir / "database.yml").write_text(
        """production:
  adapter: postgresql
  host: prod-db.example.com
  port: 5432
  database: production_db
  username: prod_user
  password: ${DB_PASSWORD}
  pool: 200
  timeout: 5000
  connect_timeout: 30
"""
    )

    # Services configuration
    (config_dir / "services.yml").write_text(
        """services:
  payment_gateway:
    url: https://api.stripe.com
    timeout_ms: 5000
    retry_count: 3

  email_service:
    url: https://api.sendgrid.com
    timeout_ms: 3000
    retry_count: 2

  analytics:
    url: https://api.segment.com
    timeout_ms: 1000
    retry_count: 1
"""
    )

    # Redis configuration
    (config_dir / "redis.conf").write_text(
        """port 6379
bind 0.0.0.0
maxmemory 4gb
maxmemory-policy allkeys-lru
appendonly yes
appendfsync everysec
"""
    )

    # SSL certificates
    certificates = {
        "certificates": [
            {
                "domain": "api.example.com",
                "issuer": "Let's Encrypt",
                "issued_date": "2024-08-01",
                "expiry_date": "2024-11-15",
                "days_remaining": 14,
                "criticality": "HIGH",
            },
            {
                "domain": "www.example.com",
                "issuer": "Let's Encrypt",
                "issued_date": "2024-09-01",
                "expiry_date": "2024-12-01",
                "days_remaining": 30,
                "criticality": "MEDIUM",
            },
            {
                "domain": "admin.example.com",
                "issuer": "Let's Encrypt",
                "issued_date": "2024-07-15",
                "expiry_date": "2025-01-15",
                "days_remaining": 75,
                "criticality": "LOW",
            },
        ]
    }
    (config_dir / "certificates.json").write_text(json.dumps(certificates, indent=2))

    # Encryption settings
    (config_dir / "encryption.yml").write_text(
        """encryption:
  algorithm: AES-256-GCM
  key_rotation_days: 90
  last_rotation: 2024-08-01

  database:
    encrypt_at_rest: true
    encryption_key_id: key-12345

  backups:
    encryption_enabled: true
    encryption_algorithm: AES-256
"""
    )

    # IAM policies
    iam_policies = {
        "policies": [
            {
                "name": "AdminAccess",
                "users": ["admin@example.com"],
                "permissions": ["*"],
                "mfa_required": True,
            },
            {
                "name": "DeveloperAccess",
                "users": ["dev1@example.com", "dev2@example.com"],
                "permissions": ["read", "write"],
                "mfa_required": False,
            },
        ]
    }
    (config_dir / "iam_policies.json").write_text(json.dumps(iam_policies, indent=2))

    # Audit configuration
    (config_dir / "audit.conf").write_text(
        """[audit]
enabled = true
log_level = INFO
log_path = /var/log/audit/audit.log
retention_days = 90

[events]
track_logins = true
track_api_calls = true
track_config_changes = true
track_data_access = true
"""
    )

    print("✓ Created config directory with configuration files")

    # ========================================================================
    # 5. Deployments Directory
    # ========================================================================
    deployments_dir = base_path / "deployments"
    deployments_dir.mkdir(exist_ok=True)

    deployment_history = {
        "deployments": [
            {
                "id": "deploy-001",
                "timestamp": "2024-10-30T14:30:00Z",
                "version": "v1.2.2",
                "status": "SUCCESS",
                "duration_seconds": 180,
            },
            {
                "id": "deploy-002",
                "timestamp": "2024-11-01T09:15:00Z",
                "version": "v1.2.3",
                "status": "SUCCESS",
                "duration_seconds": 210,
            },
        ]
    }
    (deployments_dir / "history.json").write_text(json.dumps(deployment_history, indent=2))

    # Changelog
    (deployments_dir / "changelog.txt").write_text(
        """v1.2.3 (2024-11-01)
- Added cache warming on application startup
- Optimized database queries in OrderService
- Updated Redis client library to v4.2.0

v1.2.2 (2024-10-30)
- Fixed memory leak in session management
- Improved error handling in payment processing
- Updated dependencies
"""
    )

    print("✓ Created deployments directory with deployment history")

    # ========================================================================
    # 6. Backups Directory
    # ========================================================================
    backups_dir = base_path / "backups"
    backups_dir.mkdir(exist_ok=True)

    backup_manifest = {
        "backups": [
            {
                "backup_id": "backup-20241031-0200",
                "timestamp": "2024-10-31T02:00:00Z",
                "type": "full",
                "size_gb": 120.5,
                "status": "completed",
                "retention_days": 30,
            },
            {
                "backup_id": "backup-20241101-0200",
                "timestamp": "2024-11-01T02:00:00Z",
                "type": "incremental",
                "size_gb": 8.2,
                "status": "completed",
                "retention_days": 7,
            },
        ],
        "total_backups": 45,
        "total_size_gb": 2450.5,
        "oldest_backup": "2024-09-15T02:00:00Z",
    }
    (backups_dir / "manifest.json").write_text(json.dumps(backup_manifest, indent=2))

    print("✓ Created backups directory with backup manifest")

    # ========================================================================
    # 7. Security Directory
    # ========================================================================
    security_dir = base_path / "security"
    security_dir.mkdir(exist_ok=True)

    scan_results = {
        "scan_id": "scan-20241101",
        "timestamp": "2024-11-01T08:00:00Z",
        "vulnerabilities": [
            {
                "id": "CVE-2024-12345",
                "severity": "HIGH",
                "package": "openssl",
                "current_version": "1.1.1k",
                "fixed_version": "1.1.1w",
                "description": "Buffer overflow vulnerability",
                "cvss_score": 8.1,
            },
            {
                "id": "CVE-2024-67890",
                "severity": "MEDIUM",
                "package": "nginx",
                "current_version": "1.20.1",
                "fixed_version": "1.20.2",
                "description": "HTTP request smuggling",
                "cvss_score": 5.3,
            },
            {
                "id": "CVE-2024-11111",
                "severity": "CRITICAL",
                "package": "postgresql",
                "current_version": "12.8",
                "fixed_version": "12.12",
                "description": "SQL injection vulnerability",
                "cvss_score": 9.8,
            },
        ],
        "summary": {"critical": 1, "high": 1, "medium": 1, "low": 0},
    }
    (security_dir / "scan_results.json").write_text(json.dumps(scan_results, indent=2))

    print("✓ Created security directory with scan results")

    # ========================================================================
    # 8. Billing Directory
    # ========================================================================
    billing_dir = base_path / "billing"
    billing_dir.mkdir(exist_ok=True)

    aws_costs = {
        "period": "2024-10",
        "total_cost_usd": 15420.50,
        "services": [
            {"service": "EC2", "cost_usd": 8500.00, "usage_hours": 8760},
            {"service": "RDS", "cost_usd": 3200.00, "storage_gb": 2000},
            {"service": "S3", "cost_usd": 1500.00, "storage_gb": 50000},
            {"service": "CloudFront", "cost_usd": 980.50, "data_transfer_gb": 15000},
            {"service": "Lambda", "cost_usd": 640.00, "invocations": 2000000},
            {"service": "Others", "cost_usd": 600.00},
        ],
        "budget_usd": 12000.00,
        "budget_status": "OVER_BUDGET",
    }
    (billing_dir / "aws_costs.json").write_text(json.dumps(aws_costs, indent=2))

    print("✓ Created billing directory with cost data")

    # ========================================================================
    # 9. Storage Directory
    # ========================================================================
    storage_dir = base_path / "storage"
    storage_dir.mkdir(exist_ok=True)

    storage_inventory = {
        "environments": [
            {
                "name": "production",
                "buckets": [
                    {
                        "name": "prod-user-uploads",
                        "size_gb": 5600.5,
                        "object_count": 2500000,
                        "storage_class": "STANDARD",
                        "cost_per_month_usd": 128.50,
                    },
                    {
                        "name": "prod-logs",
                        "size_gb": 8900.2,
                        "object_count": 15000000,
                        "storage_class": "STANDARD_IA",
                        "cost_per_month_usd": 89.00,
                    },
                ],
            },
            {
                "name": "staging",
                "buckets": [
                    {
                        "name": "staging-test-data",
                        "size_gb": 450.0,
                        "object_count": 50000,
                        "storage_class": "STANDARD",
                        "cost_per_month_usd": 10.35,
                    }
                ],
            },
        ]
    }
    (storage_dir / "inventory.json").write_text(json.dumps(storage_inventory, indent=2))

    print("✓ Created storage directory with inventory data")

    # ========================================================================
    # 10. State Directory
    # ========================================================================
    state_dir = base_path / "state"
    state_dir.mkdir(exist_ok=True)

    service_states = {
        "timestamp": datetime.now().isoformat(),
        "services": [
            {"name": "web-app", "status": "running", "replicas": 3, "healthy": 3},
            {"name": "auth-service", "status": "running", "replicas": 2, "healthy": 2},
            {"name": "database", "status": "running", "replicas": 1, "healthy": 1},
            {"name": "redis", "status": "running", "replicas": 1, "healthy": 1},
        ],
    }
    (state_dir / "services.json").write_text(json.dumps(service_states, indent=2))

    print("✓ Created state directory with service states")

    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "=" * 80)
    print("Sample data setup complete!")
    print("=" * 80)
    print(f"\nBase directory: {base_path.absolute()}")
    print("\nCreated directories:")
    print(f"  ✓ {logs_dir.relative_to(base_path)} - Application and system logs")
    print(f"  ✓ {metrics_dir.relative_to(base_path)} - Performance metrics")
    print(f"  ✓ {k8s_dir.relative_to(base_path)} - Kubernetes configurations")
    print(f"  ✓ {config_dir.relative_to(base_path)} - Application configurations")
    print(f"  ✓ {deployments_dir.relative_to(base_path)} - Deployment history")
    print(f"  ✓ {backups_dir.relative_to(base_path)} - Backup manifests")
    print(f"  ✓ {security_dir.relative_to(base_path)} - Security scan results")
    print(f"  ✓ {billing_dir.relative_to(base_path)} - Billing and cost data")
    print(f"  ✓ {storage_dir.relative_to(base_path)} - Storage inventory")
    print(f"  ✓ {state_dir.relative_to(base_path)} - Service states")

    print("\n" + "=" * 80)
    print("USAGE INSTRUCTIONS")
    print("=" * 80)
    print("\n1. This directory can be mounted as the working directory for evaluations:")
    print(f"   --working-directory {base_path.absolute()}")

    print("\n2. Example evaluation command:")
    print("   smoltrace-eval \\")
    print("     --model openai/gpt-4 \\")
    print("     --provider litellm \\")
    print("     --dataset kshitijthakkar/smoltrace-ops-benchmark \\")
    print(f"     --working-directory {base_path.absolute()}")

    print("\n3. All file paths in the benchmark are relative to this directory.")
    print("   For example: ./logs/app.log -> {}/logs/app.log\n".format(base_path))

    return base_path


if __name__ == "__main__":
    import sys

    # Allow custom directory name via command line
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "ops_sample"
    setup_ops_sample_data(target_dir)
