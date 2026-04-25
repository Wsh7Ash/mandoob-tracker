# Mandoob Tracker - Gulf Government Services Monitor

A crowdsourced status page for monitoring government service availability in KSA and Qatar, tracking ministry websites, Absher, Metrash2, Tamm, and Sahel platforms in real-time.

## 🌟 Features

- **Real-time Monitoring**: Continuous monitoring of government service endpoints
- **Crowdsourced Reports**: Community-driven service status reports
- **Historical Analytics**: Service availability trends and outage patterns
- **Multi-country Support**: Saudi Arabia and Qatar government services
- **Mobile-friendly**: Responsive design for mobile reporting
- **API Access**: RESTful API for integration with other systems
- **Alert System**: Email/SMS notifications for service outages
- **Dashboard Analytics**: Comprehensive monitoring dashboard

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/Wsh7Ash/mandoob-tracker
cd mandoob-tracker
pip install -r requirements.txt
```

### Configuration

```bash
# Copy configuration template
cp config/config.example.yaml config/config.yaml

# Edit configuration
nano config/config.yaml
```

### Running the System

```bash
# Start the web application
python app.py

# Start the monitoring daemon
python monitor/daemon.py

# Run API server
python api/server.py
```

## 📍 Monitored Services

### Saudi Arabia (KSA)

| Service | Platform | Status Page | Endpoint |
|---------|----------|-------------|----------|
| Absher | Interior Ministry | absher.sa | https://absher.sa |
| Muqeem | Interior Ministry | muqeem.sa | https://muqeem.sa |
| Najiz | Justice Ministry | najiz.sa | https://najiz.sa |
| Qiwa | Labor Ministry | qiwa.sa | https://qiwa.sa |
| GOSI | Social Insurance | gosi.gov.sa | https://www.gosi.gov.sa |
| Zakat | Zakat Authority | zatca.gov.sa | https://zatca.gov.sa |
| Eservices | Yesser | eservices.gov.sa | https://eservices.gov.sa |

### Qatar

| Service | Platform | Status Page | Endpoint |
|---------|----------|-------------|----------|
| Metrash2 | Ministry of Interior | metrash2.gov.qa | https://metrash2.gov.qa |
| Hukoomi | Digital Government | hukoomi.gov.qa | https://hukoomi.gov.qa |
| Qatar Portal | Government Portal | portal.gov.qa | https://portal.gov.qa |
| MoI | Ministry of Interior | moi.gov.qa | https://www.moi.gov.qa |
| MoPH | Public Health | mph.gov.qa | https://www.moph.gov.qa |

## 📡 API Endpoints

### Service Status

#### Get All Service Status
```http
GET /api/v1/services/status
```

#### Get Specific Service Status
```http
GET /api/v1/services/status/{service_id}
```

#### Get Country Services
```http
GET /api/v1/services/country/{country_code}
```

### Crowd Reports

#### Submit Service Report
```http
POST /api/v1/reports
Content-Type: application/json

{
  "service_id": "absher_sa",
  "status": "down",
  "issue_type": "login_error",
  "description": "Cannot login to Absher",
  "user_location": "Riyadh",
  "user_agent": "Mozilla/5.0...",
  "confidence": 0.9
}
```

#### Get Recent Reports
```http
GET /api/v1/reports?service_id=absher_sa&hours=24&limit=50
```

### Analytics

#### Get Service Analytics
```http
GET /api/v1/analytics/service/{service_id}?period=30d
```

#### Get Country Analytics
```http
GET /api/v1/analytics/country/{country_code}?period=7d
```

## 📊 Response Examples

### Service Status Response

```json
{
  "services": [
    {
      "id": "absher_sa",
      "name": "Absher",
      "country": "SA",
      "platform": "Interior Ministry",
      "status": "operational",
      "response_time": 245,
      "last_check": "2026-04-25T10:30:00Z",
      "uptime_percentage": 99.2,
      "recent_outages": 2,
      "next_check": "2026-04-25T10:35:00Z"
    }
  ],
  "overall_status": {
    "total_services": 12,
    "operational": 10,
    "degraded": 1,
    "down": 1,
    "last_updated": "2026-04-25T10:30:00Z"
  }
}
```

### Crowd Report Response

```json
{
  "reports": [
    {
      "id": "rpt_123456",
      "service_id": "absher_sa",
      "status": "down",
      "issue_type": "login_error",
      "description": "Cannot login to Absher platform",
      "user_location": "Riyadh",
      "timestamp": "2026-04-25T10:25:00Z",
      "confidence": 0.9,
      "verified": true,
      "affected_users": 15
    }
  ],
  "summary": {
    "total_reports": 45,
    "verified_reports": 38,
    "unique_reporters": 23,
    "time_period": "24h"
  }
}
```

## 🏗️ Architecture

```
mandoob-tracker/
├── app.py                     # Flask web application
├── monitor/
│   ├── daemon.py             # Monitoring daemon
│   ├── checker.py            # Service health checker
│   └── reporter.py           # Report processor
├── api/
│   ├── server.py             # FastAPI server
│   ├── endpoints/
│   │   ├── services.py       # Service endpoints
│   │   ├── reports.py        # Report endpoints
│   │   └── analytics.py      # Analytics endpoints
├── core/
│   ├── monitor.py            # Core monitoring logic
│   ├── analytics.py         # Analytics calculations
│   └── alerts.py             # Alert system
├── models/
│   ├── database.py           # Database models
│   ├── service.py            # Service models
│   └── report.py             # Report models
├── web/
│   ├── dashboard.html        # Main dashboard
│   ├── services.html         # Service status page
│   └── static/              # CSS/JS assets
├── config/
│   ├── config.yaml           # Main configuration
│   └── services.yaml         # Service definitions
├── data/
│   ├── services/             # Service data
│   └── reports/              # Report data
├── tests/
└── requirements.txt
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific test
pytest tests/test_monitor.py
```

## 📈 Performance Metrics

- **Monitoring Frequency**: Every 5 minutes
- **Response Time**: < 100ms for API requests
- **Uptime Tracking**: 99.9%+ accuracy
- **Alert Latency**: < 2 minutes for outage detection
- **Report Processing**: < 30 seconds for verification

## 🔧 Configuration

### Environment Variables

```yaml
# config/config.yaml
database:
  url: "postgresql://user:pass@localhost/mandoob"
  pool_size: 10

monitoring:
  check_interval: 300  # 5 minutes
  timeout: 30          # 30 seconds
  retry_count: 3

alerts:
  email_enabled: true
  sms_enabled: false
  webhook_url: "https://hooks.slack.com/..."

api:
  rate_limit: 100      # requests per minute
  cors_origins: ["*"]
  debug: false

services:
  config_file: "config/services.yaml"
  data_dir: "data/services"
```

### Service Configuration

```yaml
# config/services.yaml
services:
  absher_sa:
    name: "Absher"
    country: "SA"
    platform: "Interior Ministry"
    url: "https://absher.sa"
    endpoints:
      - path: "/"
        method: "GET"
        expected_status: 200
      - path: "/login"
        method: "POST"
        expected_status: 200
    monitoring:
      enabled: true
      check_interval: 300
      timeout: 30
    alerts:
      email: true
      sms: false
```

## 🔍 Monitoring Features

### Health Checks

- **HTTP Status**: Response code validation
- **Response Time**: Performance monitoring
- **Content Validation**: Keyword presence checks
- **SSL Certificate**: Certificate expiry monitoring
- **DNS Resolution**: Domain availability checks

### Crowd-sourced Verification

- **User Reports**: Community-driven status reports
- **Location Tracking**: Geographic issue identification
- **Confidence Scoring**: Report reliability assessment
- **Cross-verification**: Multiple source confirmation

### Analytics & Insights

- **Uptime Statistics**: Historical availability data
- **Outage Patterns**: Recurring issue identification
- **Geographic Analysis**: Regional service performance
- **Trend Analysis**: Service improvement tracking

## 📱 Mobile Integration

### Mobile App Features

- **Service Status**: Real-time service availability
- **Push Notifications**: Outage alerts
- **Report Submission**: Easy issue reporting
- **Status History**: Service performance trends

### API for Mobile

```javascript
// Get service status
const response = await fetch('/api/v1/services/status');
const services = await response.json();

// Submit report
const report = await fetch('/api/v1/reports', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    service_id: 'absher_sa',
    status: 'down',
    description: 'Login not working'
  })
});
```

## 🔒 Security Features

- **Input Validation**: Sanitize all user inputs
- **Rate Limiting**: Prevent API abuse
- **Authentication**: Optional user authentication
- **Data Privacy**: Anonymize user location data
- **Audit Logging**: Complete audit trail

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

We welcome contributions! See CONTRIBUTING.md for guidelines.

### Adding New Services

1. Add service to `config/services.yaml`
2. Implement service-specific checks in `monitor/checker.py`
3. Add tests in `tests/test_services.py`
4. Update documentation

### Improving Monitoring

1. Add new health check types in `monitor/checker.py`
2. Implement alert channels in `core/alerts.py`
3. Update analytics in `core/analytics.py`
4. Add tests for new features

## 🙏 Acknowledgments

- Saudi Digital Government for service information
- Qatar Digital Government for platform details
- Community contributors for service reports
- Open-source monitoring tools and libraries

## 📞 Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: mandoob@example.com
- **Status Page**: https://status.mandoob.org

---

**Note**: This service relies on community participation for accurate status reporting. Official service status should always be verified with the respective government platforms.
