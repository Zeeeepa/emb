#!/usr/bin/env python3
"""
Repository Difference Tool with GUI

This script provides a graphical user interface for comparing two repositories
and saving the differences in a structured way. It allows users to select
repositories using a file explorer and configure comparison options.

Usage:
    python repo_diff_gui.py
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
from pathlib import Path

# Import the comparison functions from the specialized script
try:
    from repo_diff_init_specialized import compare_repositories
    SPECIALIZED_IMPORT_SUCCESS = True
except ImportError:
    SPECIALIZED_IMPORT_SUCCESS = False


class RepositoryComparisonApp:
    """Main application class for the repository comparison GUI."""
    
    def __init__(self, root):
        """Initialize the application."""
        self.root = root
        self.root.title("Repository Comparison Tool")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
        # Set up variables
        self.original_repo_path = tk.StringVar()
        self.past_repo_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.ignore_patterns = tk.StringVar(value=".git,__pycache__,.idea,.vscode,.DS_Store")
        self.comparison_mode = tk.StringVar(value="specialized")
        self.is_comparing = False
        self.comparison_thread = None
        
        # Set default output path
        default_output = os.path.join(os.path.expanduser("~"), "repo_diff_output")
        self.output_path.set(default_output)
        
        # Create the UI
        self.create_widgets()
        self.setup_layout()
        
        # Check if specialized import was successful
        if not SPECIALIZED_IMPORT_SUCCESS:
            messagebox.showwarning(
                "Module Import Warning",
                "Could not import specialized comparison module. "
                "Basic comparison mode will be used instead."
            )
            self.comparison_mode.set("basic")
            self.specialized_radio.config(state="disabled")
    
    def create_widgets(self):
        """Create all the widgets for the UI."""
        # Style configuration
        self.style = ttk.Style()
        self.style.configure("TButton", padding=6, relief="flat", background="#ccc")
        self.style.configure("TLabel", padding=6)
        self.style.configure("TFrame", padding=10)
        
        # Main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        
        # Repository selection frames
        self.repo_frame = ttk.LabelFrame(self.main_frame, text="Repository Selection", padding=10)
        
        # Original repository selection
        self.original_repo_label = ttk.Label(self.repo_frame, text="Original Repository (Current):")
        self.original_repo_entry = ttk.Entry(self.repo_frame, textvariable=self.original_repo_path, width=50)
        self.original_repo_button = ttk.Button(
            self.repo_frame, 
            text="Browse...", 
            command=self.browse_original_repo
        )
        
        # Past repository selection
        self.past_repo_label = ttk.Label(self.repo_frame, text="Past Repository (With All Contents):")
        self.past_repo_entry = ttk.Entry(self.repo_frame, textvariable=self.past_repo_path, width=50)
        self.past_repo_button = ttk.Button(
            self.repo_frame, 
            text="Browse...", 
            command=self.browse_past_repo
        )
        
        # Output path selection
        self.output_label = ttk.Label(self.repo_frame, text="Output Directory:")
        self.output_entry = ttk.Entry(self.repo_frame, textvariable=self.output_path, width=50)
        self.output_button = ttk.Button(
            self.repo_frame, 
            text="Browse...", 
            command=self.browse_output_path
        )
        
        # Options frame
        self.options_frame = ttk.LabelFrame(self.main_frame, text="Comparison Options", padding=10)
        
        # Ignore patterns
        self.ignore_label = ttk.Label(self.options_frame, text="Ignore Patterns (comma-separated):")
        self.ignore_entry = ttk.Entry(self.options_frame, textvariable=self.ignore_patterns, width=50)
        
        # Comparison mode selection
        self.mode_label = ttk.Label(self.options_frame, text="Comparison Mode:")
        self.mode_frame = ttk.Frame(self.options_frame)
        
        self.basic_radio = ttk.Radiobutton(
            self.mode_frame, 
            text="Basic", 
            variable=self.comparison_mode, 
            value="basic"
        )
        self.enhanced_radio = ttk.Radiobutton(
            self.mode_frame, 
            text="Enhanced", 
            variable=self.comparison_mode, 
            value="enhanced"
        )
        self.specialized_radio = ttk.Radiobutton(
            self.mode_frame, 
            text="Specialized (for __init__.py)", 
            variable=self.comparison_mode, 
            value="specialized"
        )
        
        # Action buttons
        self.button_frame = ttk.Frame(self.main_frame)
        self.compare_button = ttk.Button(
            self.button_frame, 
            text="Compare Repositories", 
            command=self.start_comparison,
            style="TButton"
        )
        self.open_output_button = ttk.Button(
            self.button_frame, 
            text="Open Output Directory", 
            command=self.open_output_directory,
            state="disabled"
        )
        
        # Progress and log area
        self.progress_frame = ttk.LabelFrame(self.main_frame, text="Progress", padding=10)
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, 
            orient="horizontal", 
            length=100, 
            mode="indeterminate"
        )
        self.log_area = scrolledtext.ScrolledText(
            self.progress_frame, 
            wrap=tk.WORD, 
            width=70, 
            height=10,
            state="disabled"
        )
        
    def setup_layout(self):
        """Set up the layout of the widgets."""
        # Main frame
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Repository selection frame
        self.repo_frame.pack(fill=tk.X, pady=5)
        
        # Original repository
        self.original_repo_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        self.original_repo_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=5)
        self.original_repo_button.grid(row=0, column=2, sticky=tk.E, pady=5)
        
        # Past repository
        self.past_repo_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        self.past_repo_entry.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=5)
        self.past_repo_button.grid(row=1, column=2, sticky=tk.E, pady=5)
        
        # Output path
        self.output_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        self.output_entry.grid(row=2, column=1, sticky=tk.EW, pady=5, padx=5)
        self.output_button.grid(row=2, column=2, sticky=tk.E, pady=5)
        
        # Configure grid weights
        self.repo_frame.columnconfigure(1, weight=1)
        
        # Options frame
        self.options_frame.pack(fill=tk.X, pady=5)
        
        # Ignore patterns
        self.ignore_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        self.ignore_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=5)
        
        # Comparison mode
        self.mode_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        self.mode_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        self.basic_radio.pack(side=tk.LEFT, padx=5)
        self.enhanced_radio.pack(side=tk.LEFT, padx=5)
        self.specialized_radio.pack(side=tk.LEFT, padx=5)
        
        # Configure grid weights
        self.options_frame.columnconfigure(1, weight=1)
        
        # Action buttons
        self.button_frame.pack(fill=tk.X, pady=10)
        self.compare_button.pack(side=tk.LEFT, padx=5)
        self.open_output_button.pack(side=tk.LEFT, padx=5)
        
        # Progress and log area
        self.progress_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.progress_bar.pack(fill=tk.X, pady=5)
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=5)
    
    def browse_original_repo(self):
        """Open a file dialog to select the original repository."""
        path = filedialog.askdirectory(title="Select Original Repository")
        if path:
            self.original_repo_path.set(path)
    
    def browse_past_repo(self):
        """Open a file dialog to select the past repository."""
        path = filedialog.askdirectory(title="Select Past Repository")
        if path:
            self.past_repo_path.set(path)
    
    def browse_output_path(self):
        """Open a file dialog to select the output directory."""
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_path.set(path)
    
    def open_output_directory(self):
        """Open the output directory in the file explorer."""
        output_dir = self.output_path.get()
        if not os.path.exists(output_dir):
            messagebox.showerror("Error", "Output directory does not exist.")
            return
        
        # Open the directory using the appropriate command for the OS
        if sys.platform == 'win32':
            os.startfile(output_dir)
        elif sys.platform == 'darwin':  # macOS
            subprocess.run(['open', output_dir])
        else:  # Linux
            subprocess.run(['xdg-open', output_dir])
    
    def log_message(self, message):
        """Add a message to the log area."""
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state="disabled")
    
    def validate_inputs(self):
        """Validate user inputs before starting comparison."""
        # Check if repositories are selected
        if not self.original_repo_path.get():
            messagebox.showerror("Error", "Please select the original repository.")
            return False
        
        if not self.past_repo_path.get():
            messagebox.showerror("Error", "Please select the past repository.")
            return False
        
        # Check if repositories exist
        if not os.path.isdir(self.original_repo_path.get()):
            messagebox.showerror("Error", "Original repository path is not a valid directory.")
            return False
        
        if not os.path.isdir(self.past_repo_path.get()):
            messagebox.showerror("Error", "Past repository path is not a valid directory.")
            return False
        
        # Check if output path is set
        if not self.output_path.get():
            messagebox.showerror("Error", "Please select an output directory.")
            return False
        
        return True
    
    def start_comparison(self):
        """Start the repository comparison process."""
        if not self.validate_inputs():
            return
        
        if self.is_comparing:
            messagebox.showinfo("Info", "Comparison is already in progress.")
            return
        
        # Disable UI elements during comparison
        self.is_comparing = True
        self.compare_button.config(state="disabled")
        self.open_output_button.config(state="disabled")
        
        # Clear log area
        self.log_area.config(state="normal")
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state="disabled")
        
        # Start progress bar
        self.progress_bar.start()
        
        # Get parameters
        original_repo = self.original_repo_path.get()
        past_repo = self.past_repo_path.get()
        output_path = self.output_path.get()
        ignore_list = [item.strip() for item in self.ignore_patterns.get().split(',') if item.strip()]
        mode = self.comparison_mode.get()
        
        # Log start of comparison
        self.log_message(f"Starting repository comparison...")
        self.log_message(f"Original repository: {original_repo}")
        self.log_message(f"Past repository: {past_repo}")
        self.log_message(f"Output directory: {output_path}")
        self.log_message(f"Ignoring: {ignore_list}")
        self.log_message(f"Comparison mode: {mode}")
        self.log_message("-----------------------------------")
        
        # Start comparison in a separate thread
        self.comparison_thread = threading.Thread(
            target=self.run_comparison,
            args=(original_repo, past_repo, output_path, ignore_list, mode)
        )
        self.comparison_thread.daemon = True
        self.comparison_thread.start()
    
    def run_comparison(self, original_repo, past_repo, output_path, ignore_list, mode):
        """Run the repository comparison in a separate thread."""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_path, exist_ok=True)
            
            # Choose the appropriate comparison method based on the selected mode
            if mode == "specialized" and SPECIALIZED_IMPORT_SUCCESS:
                # Use the imported function if available
                self.log_message("Using specialized comparison for __init__.py files...")
                files_compared, files_with_diff, files_only_in_past = compare_repositories(
                    original_repo, past_repo, output_path, ignore_list
                )
                success = True
            else:
                # Otherwise, run the appropriate script as a subprocess
                script_name = {
                    "basic": "repo_diff.py",
                    "enhanced": "repo_diff_enhanced.py",
                    "specialized": "repo_diff_init_specialized.py"
                }.get(mode, "repo_diff.py")
                
                self.log_message(f"Running {script_name}...")
                
                # Get the script path (assuming it's in the same directory as this script)
                script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)
                
                # Run the script as a subprocess
                cmd = [sys.executable, script_path, original_repo, past_repo, output_path]
                if ignore_list:
                    cmd.extend(["--ignore"] + ignore_list)
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                
                # Process output in real-time
                for line in process.stdout:
                    self.log_message(line.strip())
                
                # Wait for the process to complete
                process.wait()
                
                # Check if the process was successful
                success = process.returncode == 0
                
                # Process any error output
                for line in process.stderr:
                    self.log_message(f"ERROR: {line.strip()}")
                
                # Set placeholder values since we don't have the actual counts
                files_compared = files_with_diff = files_only_in_past = -1
            
            # Update UI after comparison is complete
            self.root.after(0, self.comparison_complete, success, output_path, 
                           files_compared, files_with_diff, files_only_in_past)
            
        except Exception as e:
            # Handle any exceptions
            error_message = f"Error during comparison: {str(e)}"
            self.root.after(0, self.comparison_error, error_message)
    
    def comparison_complete(self, success, output_path, files_compared, files_with_diff, files_only_in_past):
        """Handle completion of the comparison process."""
        # Stop progress bar
        self.progress_bar.stop()
        
        # Log completion
        if success:
            self.log_message("-----------------------------------")
            self.log_message("Comparison completed successfully!")
            
            if files_compared >= 0:
                self.log_message(f"Files compared: {files_compared}")
                self.log_message(f"Files with differences: {files_with_diff}")
                self.log_message(f"Files only in past repository: {files_only_in_past}")
                self.log_message(f"Total differences: {files_with_diff + files_only_in_past}")
            
            self.log_message(f"Differences saved to: {output_path}")
            
            # Enable the open output button
            self.open_output_button.config(state="normal")
            
            # Show success message
            messagebox.showinfo(
                "Comparison Complete", 
                f"Repository comparison completed successfully!\n\n"
                f"Differences saved to: {output_path}"
            )
        else:
            self.log_message("-----------------------------------")
            self.log_message("Comparison failed. See log for details.")
            
            # Show error message
            messagebox.showerror(
                "Comparison Failed", 
                "Repository comparison failed. See log for details."
            )
        
        # Re-enable UI elements
        self.is_comparing = False
        self.compare_button.config(state="normal")
    
    def comparison_error(self, error_message):
        """Handle errors during the comparison process."""
        # Stop progress bar
        self.progress_bar.stop()
        
        # Log error
        self.log_message("-----------------------------------")
        self.log_message(error_message)
        self.log_message("Comparison failed.")
        
        # Show error message
        messagebox.showerror("Error", error_message)
        
        # Re-enable UI elements
        self.is_comparing = False
        self.compare_button.config(state="normal")


def main():
    """Main function to start the application."""
    root = tk.Tk()
    app = RepositoryComparisonApp(root)
    
    # Set icon if available
    try:
        # Try to use a standard icon
        root.iconbitmap(default="")
    except:
        pass
    
    # Start the main loop
    root.mainloop()


if __name__ == "__main__":
    main()