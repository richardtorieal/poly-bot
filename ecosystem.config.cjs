module.exports = {
  apps: [
    {
      name: "poly-bot",
      script: "./src/main.py",
      interpreter: "./venv/bin/python3",
      args: "run --strategy negative-risk --margin-threshold 0.005 --polling-interval 900",
      cwd: "/Users/richardanderson/projects/poly-bot",
      env: {
        PYTHONPATH: ".",
        NODE_ENV: "production"
      },
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      log_date_format: "YYYY-MM-DD HH:mm:ss"
    },
    {
      name: "poly-bot-btc-trend",
      script: "paper_trade_audit.py",
      args: "--strategy btc_trend --ledger logs/ledger_btc_trend.json",
      interpreter: "./venv/bin/python3",
      cwd: "/Users/richardanderson/projects/poly-bot",
      env: {
        PYTHONPATH: ".",
        NODE_ENV: "production"
      },
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      log_date_format: "YYYY-MM-DD HH:mm:ss"
    },
    {
      name: "poly-bot-sniper",
      script: "paper_trade_audit.py",
      args: "--strategy sniper_v3 --ledger logs/ledger_sniper_v3.json",
      interpreter: "./venv/bin/python3",
      cwd: "/Users/richardanderson/projects/poly-bot",
      env: {
        PYTHONPATH: ".",
        NODE_ENV: "production"
      },
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      log_date_format: "YYYY-MM-DD HH:mm:ss"
    },
    {
      name: "poly-bot-scalper",
      script: "paper_trade_audit.py",
      args: "--strategy scalper_v1 --ledger logs/ledger_scalper_v1.json",
      interpreter: "./venv/bin/python3",
      cwd: "/Users/richardanderson/projects/poly-bot",
      env: {
        PYTHONPATH: ".",
        NODE_ENV: "production"
      },
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      log_date_format: "YYYY-MM-DD HH:mm:ss"
    }
  ]
}
