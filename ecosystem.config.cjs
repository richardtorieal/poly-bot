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
      name: "btc-paper-trader",
      script: "paper_trade_audit.py",
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
