# AgentGen Integration with Codegen

This directory contains scripts and documentation for integrating AgentGen with the Codegen application.

## Integration Scripts

1. `integrate_with_codegen.sh` - Integrates AgentGen with Codegen by copying the AgentGen module into the Codegen repository.
2. `update_codegen_app.sh` - Updates the imports in the codegen_app to use the integrated AgentGen module.

## Usage

### Step 1: Integrate AgentGen with Codegen

```bash
# Make the script executable
chmod +x integrate_with_codegen.sh

# Run the script with the path to the codegen repository
./integrate_with_codegen.sh /path/to/codegen
```

This script will:
- Copy the AgentGen module into the Codegen repository
- Create the necessary `__init__.py` file
- Update the Codegen pyproject.toml to include AgentGen as a dependency
- Install Codegen with the integrated AgentGen

### Step 2: Update the codegen_app imports

```bash
# Make the script executable
chmod +x update_codegen_app.sh

# Run the script with the path to the codegen_app directory
./update_codegen_app.sh /path/to/codegen_app
```

This script will:
- Create a backup of the original app.py file
- Update the imports to use the integrated AgentGen module
- Verify that the imports were updated correctly

## Manual Integration

If you prefer to integrate AgentGen with Codegen manually, please refer to the `INTEGRATION.md` file for detailed instructions.

## Troubleshooting

If you encounter any issues during the integration process, please check the following:

1. Ensure that both Codegen and AgentGen are installed in your environment:
   ```bash
   pip list | grep -E 'codegen|agentgen'
   ```

2. Check the Python path:
   ```python
   import sys
   print(sys.path)
   ```

3. Ensure all necessary `__init__.py` files exist in the directory structure.

4. If you encounter import errors, try reinstalling both packages:
   ```bash
   cd /path/to/codegen
   pip install -e .
   
   cd /path/to/AgentGen
   pip install -e .
   ```