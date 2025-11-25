# Job Finder Script

This Python script allows anyone to automatically find Python, Django, and freelancing jobs from multiple global job platforms and get notified by email.

## Features
- Searches multiple RSS feeds for Python/Django jobs
- Filters jobs by keywords like `python`, `django`, `freelance`, `fast job`
- Sends email notifications when new jobs match your criteria
- Works without storing jobs in a database (optional tracking available)

## How to Use
1. **Download the script** or clone the repository:
```bash
git clone <repo-url>
cd <repo-folder>
```
2. **Install required Python packages**:
```bash
pip install requests feedparser beautifulsoup4
```
3. **Configure email settings** inside the script:
- `SMTP_USER`: Your email address
- `SMTP_PASS`: Your app password (for Gmail or other providers)
- `EMAIL_TO`: The email that will receive job alerts

4. **Run the script**:
```bash
python3 job_agent.py
```
- The script will fetch new jobs from all configured feeds and send them to your email.

## Configuration
- `KEYWORDS`: Modify to search for specific job terms.
- `CUSTOM_FEEDS`: Add or remove RSS feeds as desired.
- `MIN_KEYWORD_MATCH`: Number of keywords that must match for the job to be sent.

## Running Automatically
- On **PythonAnywhere**: Schedule as a task to run periodically.
- On **Linux/Mac**: Use `cron`.
- On **Windows**: Use Task Scheduler.

## Notes
- Some platforms may block automated requests; the script relies mostly on working RSS feeds.
- Using an app password is recommended for Gmail SMTP.

## License
MIT License
