# Codegen App

This is a Modal application that deploys a FastAPI server for the Codegen application.

## Installation

1. Install dependencies:
```bash
chmod +x install_dependencies.sh
./install_dependencies.sh
```

2. Deploy to Modal:
```bash
chmod +x local_deploy.sh
./local_deploy.sh
```

## Troubleshooting

### Import Issues

If you encounter import errors with `agentgen` or `codegen`, try the following:

1. Create a symbolic link from `agentgen` to `AgentGen`:
```bash
chmod +x fix_agentgen_symlink.sh
./fix_agentgen_symlink.sh
```

2. Set up your Python path:
```bash
export PYTHONPATH=$PYTHONPATH:~/emb:~/emb/AgentGen:~/emb/codegen
```

3. Install packages in development mode:
```bash
cd ~/emb/AgentGen && pip install -e .
cd ~/emb/codegen && pip install -e .
```

### Modal Deployment Issues

If you encounter issues with Modal deployment:

1. Make sure you have the Modal CLI installed:
```bash
pip install modal
```

2. Make sure you're logged in to Modal:
```bash
modal token new
```

3. Try using the deployment script:
```bash
./local_deploy.sh
```