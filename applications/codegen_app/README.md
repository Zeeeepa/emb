# Codegen App

This is a Modal application that integrates Codegen and AgentGen to provide code analysis and generation capabilities.

## Installation

### Prerequisites

- Python 3.10+
- Modal CLI (`pip install modal`)
- Git

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Zeeeepa/emb.git
   cd emb
   ```

2. Make the installation and deployment scripts executable:
   ```bash
   chmod +x applications/codegen_app/install_dependencies.sh
   chmod +x applications/codegen_app/local_deploy.sh
   ```

3. Install dependencies:
   ```bash
   cd applications/codegen_app
   ./install_dependencies.sh
   ```

4. Deploy the app:
   ```bash
   ./local_deploy.sh
   ```

## Troubleshooting

### ModuleNotFoundError: No module named 'agentgen'

If you encounter this error, it's likely due to a case-sensitivity issue between the directory name `AgentGen` and the package name `agentgen`. The installation script should create a symbolic link to fix this, but if it fails, you can create it manually:

```bash
ln -s ~/emb/AgentGen ~/emb/agentgen
```

Then try deploying again:

```bash
./local_deploy.sh
```

### Other Import Issues

If you're still having import issues, make sure your PYTHONPATH includes both the codegen and agentgen directories:

```bash
export PYTHONPATH=$PYTHONPATH:~/emb/AgentGen:~/emb/codegen:~/emb
```

Then try deploying again.

## Development

To make changes to the app:

1. Edit the files in `applications/codegen_app/`
2. Run `./local_deploy.sh` to deploy your changes

## License

This project is licensed under the terms of the MIT license.