#!/bin/bash

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get the current directory
CURRENT_DIR=$(pwd)
print_message "Current directory: $CURRENT_DIR"

# Check if we're in the emb directory or a subdirectory
if [[ "$CURRENT_DIR" == *"/emb"* ]]; then
    # Go up to the parent directory of emb
    cd "$(echo $CURRENT_DIR | sed 's/\/emb.*//')"
    print_message "Changed to parent directory: $(pwd)"
else
    print_warning "Not in emb directory. Will clone to current location."
fi

# Check if emb directory exists
if [ -d "emb" ]; then
    print_warning "emb directory exists. Removing..."
    rm -rf emb
    if [ $? -ne 0 ]; then
        print_error "Failed to remove emb directory. Please check permissions."
        exit 1
    fi
    print_message "Successfully removed emb directory."
fi

# Clone the repository
print_message "Cloning emb repository..."
git clone https://github.com/Zeeeepa/emb
if [ $? -ne 0 ]; then
    print_error "Failed to clone repository. Please check your internet connection and try again."
    exit 1
fi

# Navigate to the emb directory
print_message "Navigating to emb directory..."
cd emb
if [ $? -ne 0 ]; then
    print_error "Failed to navigate to emb directory."
    exit 1
fi

print_message "Successfully cloned and navigated to emb repository at: $(pwd)"
print_message "To navigate to AgentGen directory, run: cd AgentGen"

# List contents of the directory
print_message "Contents of emb directory:"
ls -la