#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
  echo -e "${BLUE}[UPDATE]${NC} $1"
}

print_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Check if codegen_app directory is provided
if [ $# -eq 0 ]; then
  print_error "Please provide the path to the codegen_app directory."
  echo "Usage: $0 /path/to/codegen_app"
  exit 1
fi

CODEGEN_APP_DIR=$1

# Check if the provided directory exists
if [ ! -d "$CODEGEN_APP_DIR" ]; then
  print_error "The directory $CODEGEN_APP_DIR does not exist."
  exit 1
fi

# Check if app.py exists in the provided directory
if [ ! -f "$CODEGEN_APP_DIR/app.py" ]; then
  print_error "The file app.py does not exist in $CODEGEN_APP_DIR."
  exit 1
fi

print_message "Updating imports in $CODEGEN_APP_DIR/app.py..."

# Create a backup of the original file
cp "$CODEGEN_APP_DIR/app.py" "$CODEGEN_APP_DIR/app.py.bak"
print_message "Created backup at $CODEGEN_APP_DIR/app.py.bak"

# Update the imports
sed -i 's/from agentgen import/from codegen.agentgen import/g' "$CODEGEN_APP_DIR/app.py"
sed -i 's/from agentgen\./from codegen.agentgen./g' "$CODEGEN_APP_DIR/app.py"

print_success "Updated imports in $CODEGEN_APP_DIR/app.py"
print_message "You can now run the application with the integrated AgentGen module."

# Check if the update was successful
if grep -q "from codegen.agentgen import" "$CODEGEN_APP_DIR/app.py"; then
  print_success "Import statements successfully updated!"
else
  print_warning "Import statements may not have been updated correctly."
  print_message "Please check $CODEGEN_APP_DIR/app.py manually."
fi