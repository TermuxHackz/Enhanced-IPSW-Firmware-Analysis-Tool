#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import shutil
import threading
import tempfile
from datetime import datetime
import json
import zipfile
import hashlib
from pathlib import Path
import re
from collections import defaultdict
import requests
import sys
import logging
import traceback
from PIL import Image, ImageTk
import traceback
import webbrowser  
from PIL import Image, ImageTk 

def setup_logging():
    """Initialize application logging"""
    # Determine log directory
    if getattr(sys, 'frozen', False):
        # If running as app bundle
        app_dir = os.path.dirname(sys.executable)
        log_dir = os.path.expanduser('~/Library/Logs/IPSWComparisonTool')
    else:
        # If running as script
        app_dir = os.path.dirname(os.path.abspath(__file__))
        log_dir = os.path.join(app_dir, 'logs')
        
    # Create logs directory
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log file with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'app_{timestamp}.log')
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return log_file

# Initialize logging
log_file = setup_logging()
logging.info("Application starting")

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class IPSWComparerGUI:
    def __init__(self, root):
        logging.info("Initializing main application")
        self.root = root
        self.root.title("IPSW Firmware Comparer")
        self.root.geometry("1000x800")
        
        # Initialize variables
        self.current_version = "1.0.1"
        self.github_repo = "TermuxHackz/Enhanced-IPSW-Firmware-Analysis-Tool"
        self.current_theme = "dark"
        self.temp_dir = None
        self.comparison_running = False
        
        # Initialize path variables
        self.ipsw1_path = tk.StringVar()
        self.ipsw2_path = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready for analysis")
        
        # Load resources
        try:
            self._load_resources()
        except Exception as e:
            logging.error(f"Failed to load resources: {e}")
            self.logo_image = None
            self.logo_small = None
            
        # Initialize theme
        try:
            self._initialize_theme()
        except Exception as e:
            logging.error(f"Failed to initialize theme: {e}")
            
        # Load knowledge bases
        self._initialize_knowledge_bases()
        
        # Create GUI
        try:
            self._create_gui()
            self._create_menubar()
        except Exception as e:
            logging.error(f"Failed to create GUI: {e}")
            raise
            
        logging.info("Application initialized successfully")

    def _load_resources(self):
        """Load application resources"""
        logging.info("Loading application resources")
        try:
            image_path = get_resource_path('compare.png')
            if os.path.exists(image_path):
                # Use PIL to load the image
                pil_image = Image.open(image_path)
                self.logo_image = ImageTk.PhotoImage(pil_image)
                # Create smaller version for UI
                small_image = pil_image.resize((32, 32), Image.LANCZOS)
                self.logo_small = ImageTk.PhotoImage(small_image)
                self.logo_about = ImageTk.PhotoImage(
                    pil_image.resize((64, 64), Image.LANCZOS)
                )
            else:
                logging.warning(f"Image file not found: {image_path}")
                self.logo_image = None
                self.logo_small = None
                self.logo_about = None
        except Exception as e:
            logging.error(f"Error loading resources: {e}")
            raise

    def _initialize_theme(self):
        """Initialize application theme"""
        self.style = ttk.Style()
        try:
            # Load theme
            theme_path = get_resource_path('forest-dark.tcl')
            if os.path.exists(theme_path):
                self.root.tk.call('source', theme_path)
                self.style.theme_use('forest-dark')
            
            # Configure styles
            self.style.configure('TButton', padding=6)
            self.style.configure('Header.TLabel', font=('Helvetica', 16, 'bold'))
            self.style.configure('Action.TButton', 
                               font=('Helvetica', 10, 'bold'),
                               padding=10)
            
        except Exception as e:
            logging.error(f"Failed to load custom theme: {e}")
            self.style.theme_use('default')
    
    def _initialize_knowledge_bases(self):
        """Initialize knowledge bases for analysis"""
        logging.info("Initializing knowledge bases")
        
        self.component_knowledge = {
            'kernelcache': {
                'description': 'Core operating system kernel',
                'impact': {
                    'security': 'May contain critical security patches and vulnerability fixes',
                    'performance': 'Could affect system stability and overall device performance',
                    'battery': 'Might impact power management and battery life',
                    'features': 'May enable or modify kernel-level features'
                }
            },
            'iBoot': {
                'description': 'Bootloader responsible for system initialization',
                'impact': {
                    'security': 'Changes could affect secure boot chain and system security',
                    'performance': 'May modify boot time and system initialization',
                    'recovery': 'Could impact device recovery and update procedures'
                }
            },
            'trustcache': {
                'description': 'Security certificate and trust management system',
                'impact': {
                    'security': 'Updates to security certificates and trust relationships',
                    'compatibility': 'May affect app signing verification and system trust',
                    'features': 'Could modify allowed system operations and app capabilities'
                }
            },
            'root_hash': {
                'description': 'System integrity verification component',
                'impact': {
                    'security': 'Changes in system file verification mechanism',
                    'integrity': 'Updates to system integrity checking',
                    'recovery': 'May affect system restore and recovery processes'
                }
            }
        }
        
        self.ai_knowledge_base = {
            'system_patterns': {
                'security': {
                    'patterns': [
                        r'.*trustcache.*',
                        r'.*security.*',
                        r'.*crypto.*',
                        r'.*certificate.*',
                        r'.*auth.*',
                        r'.*protect.*',
                        r'.*seal.*'
                    ],
                    'explanation': "Security-related changes typically indicate improvements in system protection, "
                                 "vulnerability patches, or updates to security mechanisms."
                },
                'performance': {
                    'patterns': [
                        r'.*kernel.*',
                        r'.*cache.*',
                        r'.*dyld.*',
                        r'.*perf.*',
                        r'.*daemon.*',
                        r'.*service.*'
                    ],
                    'explanation': "Performance-related changes often involve optimizations to system components, "
                                 "improved resource management, or enhanced processing efficiency."
                },
                'features': {
                    'patterns': [
                        r'.*framework.*',
                        r'.*api.*',
                        r'.*service.*',
                        r'.*capability.*',
                        r'.*function.*'
                    ],
                    'explanation': "Feature-related changes typically introduce new capabilities, enhance existing "
                                 "functionality, or modify system behaviors."
                }
            },
            'component_interactions': {
                'kernelcache + trustcache': {
                    'impact': "Combined changes to kernel and trust components suggest significant system-level "
                             "security updates.",
                    'recommendation': "This update is highly recommended for security reasons."
                },
                'iBoot + kernelcache': {
                    'impact': "Changes to both boot process and kernel indicate fundamental system modifications.",
                    'recommendation': "Consider this a major system update with significant improvements."
                }
            },
            'change_patterns': {
                'large_scale': {
                    'threshold': 20,
                    'explanation': "The large number of changes suggests a significant system update that may "
                                 "include multiple improvements across security, performance, and features."
                },
                'security_focused': {
                    'indicators': ['trustcache', 'seal', 'crypto'],
                    'explanation': "This appears to be a security-focused update that strengthens system protection."
                },
                'feature_update': {
                    'indicators': ['framework', 'service', 'api'],
                    'explanation': "This update seems to focus on feature enhancements and new capabilities."
                }
            }
        }
        
        logging.info("Knowledge bases initialized successfully")

    def _create_gui(self):
        """Create the main GUI elements"""
        logging.info("Creating main GUI elements")
        try:
            # Main container frame
            main_frame = ttk.Frame(self.root, padding="10")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # Create main sections
            self._create_header(main_frame)
            self._create_file_selection(main_frame)
            self._create_progress_section(main_frame)
            self._create_results_section(main_frame)
            self._create_footer(main_frame)
            
            # Configure weights for resizing
            main_frame.columnconfigure(1, weight=1)
            self.root.columnconfigure(0, weight=1)
            self.root.rowconfigure(0, weight=1)
            
            logging.info("GUI elements created successfully")
            
        except Exception as e:
            logging.error(f"Error creating GUI: {e}")
            raise

    def _create_header(self, parent):
        """Create header section with logo and title"""
        try:
            header_frame = ttk.Frame(parent)
            header_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
            
            # Add logo if available
            if hasattr(self, 'logo_small') and self.logo_small:
                logo_label = ttk.Label(header_frame, image=self.logo_small)
                logo_label.pack(side=tk.LEFT, padx=(0, 10))
            
            # Title
            header_label = ttk.Label(
                header_frame,
                text="Enhanced IPSW Firmware Analysis Tool",
                style='Header.TLabel'
            )
            header_label.pack(side=tk.LEFT)
            
            # Toolbar frame
            toolbar_frame = ttk.Frame(header_frame)
            toolbar_frame.pack(side=tk.RIGHT, padx=5)
            
            # Toolbar buttons
            export_button = ttk.Button(
                toolbar_frame,
                text="Export",
                command=self._export_analysis,
                style='Toolbar.TButton'
            )
            export_button.pack(side=tk.RIGHT, padx=2)
            
            update_button = ttk.Button(
                toolbar_frame,
                text="Update",
                command=self._check_updates,
                style='Toolbar.TButton'
            )
            update_button.pack(side=tk.RIGHT, padx=2)
            
        except Exception as e:
            logging.error(f"Error creating header: {e}")
            raise

    def _create_file_selection(self, parent):
        """Create the file selection section"""
        selection_frame = ttk.LabelFrame(parent, text="Firmware Selection", padding="5")
        selection_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # First IPSW
        ttk.Label(selection_frame, text="First IPSW:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(selection_frame, textvariable=self.ipsw1_path).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(
            selection_frame,
            text="Browse",
            command=lambda: self._browse_file(self.ipsw1_path)
        ).grid(row=0, column=2)
        
        # Second IPSW
        ttk.Label(selection_frame, text="Second IPSW:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(selection_frame, textvariable=self.ipsw2_path).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(
            selection_frame,
            text="Browse",
            command=lambda: self._browse_file(self.ipsw2_path)
        ).grid(row=1, column=2)
        
        # Add analyze button
        self.compare_button = ttk.Button(
            selection_frame,
            text="Analyze Firmware Files",
            command=self._start_comparison,
            style='Action.TButton'  # Special style for primary action
        )
        self.compare_button.grid(row=2, column=0, columnspan=3, pady=10)
        
        # Configure grid weights
        selection_frame.columnconfigure(1, weight=1)
        
        # Configure button style
        self.style.configure('Action.TButton', 
                           font=('Helvetica', 10, 'bold'),
                           padding=10)
        
        return selection_frame
    
    def _export_json(self, filename):
        """Export analysis as JSON"""
        try:
            data = {
                'summary': self.summary_text.get('1.0', tk.END),
                'technical': self.technical_text.get('1.0', tk.END),
                'impact': self.impact_text.get('1.0', tk.END),
                'metadata': {
                    'date': datetime.now().isoformat(),
                    'ipsw1': self.ipsw1_path.get(),
                    'ipsw2': self.ipsw2_path.get()
                }
            }
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logging.error(f"Error exporting to JSON: {e}")
            raise

    def _export_html(self, filename):
        """Export analysis as HTML"""
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>IPSW Firmware Analysis Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    h1, h2 {{ color: #333; }}
                    .section {{ margin: 20px 0; padding: 20px; background: #f9f9f9; border-radius: 5px; }}
                    pre {{ white-space: pre-wrap; }}
                </style>
            </head>
            <body>
                <h1>IPSW Firmware Analysis Report</h1>
                <div class="section">
                    <h2>Summary</h2>
                    <pre>{self.summary_text.get('1.0', tk.END)}</pre>
                </div>
                <div class="section">
                    <h2>Technical Details</h2>
                    <pre>{self.technical_text.get('1.0', tk.END)}</pre>
                </div>
                <div class="section">
                    <h2>Impact Analysis</h2>
                    <pre>{self.impact_text.get('1.0', tk.END)}</pre>
                </div>
                <footer>
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </footer>
            </body>
            </html>
            """
            with open(filename, 'w') as f:
                f.write(html_content)
        except Exception as e:
            logging.error(f"Error exporting to HTML: {e}")
            raise

    def _export_text(self, filename):
        """Export analysis as plain text"""
        try:
            with open(filename, 'w') as f:
                f.write("=== IPSW Firmware Analysis Report ===\n\n")
                f.write("SUMMARY\n")
                f.write("=======\n")
                f.write(self.summary_text.get('1.0', tk.END))
                f.write("\nTECHNICAL DETAILS\n")
                f.write("=================\n")
                f.write(self.technical_text.get('1.0', tk.END))
                f.write("\nIMPACT ANALYSIS\n")
                f.write("===============\n")
                f.write(self.impact_text.get('1.0', tk.END))
        except Exception as e:
            logging.error(f"Error exporting to text: {e}")
            raise

    def _verify_theme_resources(self):
        """Verify theme resources are available"""
        try:
            theme_file = get_resource_path('forest-dark.tcl')
            theme_dir = get_resource_path('forest-dark')
            
            logging.info("Checking theme resources:")
            logging.info(f"Theme file: {theme_file} (exists: {os.path.exists(theme_file)})")
            logging.info(f"Theme directory: {theme_dir} (exists: {os.path.exists(theme_dir)})")
            
            if os.path.exists(theme_dir):
                logging.info("Theme directory contents:")
                for item in os.listdir(theme_dir):
                    logging.info(f"- {item}")
            
            # Check if specific theme images exist
            required_images = ['checkbox-checked.png', 'checkbox-unchecked.png', 
                             'radio-checked.png', 'radio-unchecked.png']
            for image in required_images:
                image_path = os.path.join(theme_dir, image)
                logging.info(f"Image {image}: exists={os.path.exists(image_path)}")
                
            return os.path.exists(theme_file) and os.path.exists(theme_dir)
            
        except Exception as e:
            logging.error(f"Error verifying theme resources: {e}")
            return False
    
    def _create_menubar(self):
        """Create the application menubar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Add logo to file menu if available
        if hasattr(self, 'logo_small') and self.logo_small:
            file_menu.add_command(
                label="New Comparison",
                image=self.logo_small,
                compound=tk.LEFT,
                command=self._reset_comparison
            )
        else:
            file_menu.add_command(label="New Comparison", command=self._reset_comparison)
        
        file_menu.add_separator()
        file_menu.add_command(label="Export Analysis", command=self._export_analysis)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Technical Details", command=self._show_technical_details)
        view_menu.add_command(label="Impact Summary", command=self._show_impact_summary)
        
        # Theme submenu in View menu
        theme_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Theme", menu=theme_menu)
        theme_menu.add_command(label="Light Theme", command=lambda: self._set_theme("light"))
        theme_menu.add_command(label="Dark Theme", command=lambda: self._set_theme("dark"))
        
        # Tools Menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Reset Comparison", command=self._reset_comparison)
        tools_menu.add_command(label="Clear Cache", command=self._cleanup)
        
        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        if hasattr(self, 'logo_small') and self.logo_small:
            help_menu.add_command(
                label="About",
                image=self.logo_small,
                compound=tk.LEFT,
                command=self._show_about
            )
        else:
            help_menu.add_command(label="About", command=self._show_about)
            
        help_menu.add_command(label="Documentation", command=self._show_documentation)
        help_menu.add_separator()
        help_menu.add_command(label="Check for Updates", command=self._check_updates)

    def _create_context_menu(self, parent):
        """Create context menu for right-click"""
        self.context_menu = tk.Menu(parent, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self._copy_selection)
        self.context_menu.add_command(label="Export Selection", command=self._export_selection)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Clear", command=self._clear_selection)
        
        # Bind right-click to show context menu
        parent.bind("<Button-3>", self._show_context_menu)

    def _show_context_menu(self, event):
        """Show context menu on right-click"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _copy_selection(self):
        """Copy selected text to clipboard"""
        try:
            selected_text = self.root.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
        except:
            pass

    def _export_selection(self):
        """Export selected text to file"""
        try:
            selected_text = self.root.selection_get()
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if filename:
                with open(filename, 'w') as f:
                    f.write(selected_text)
        except:
            pass

    def _clear_selection(self):
        """Clear current selection"""
        try:
            widget = self.root.focus_get()
            if hasattr(widget, 'selection_clear'):
                widget.selection_clear()
        except:
            pass

    def _show_technical_details(self):
        """Switch to technical details tab"""
        self.results_notebook.select(1)  # Select technical details tab

    def _show_impact_summary(self):
        """Switch to impact analysis tab"""
        self.results_notebook.select(2)  # Select impact analysis tab

    def _set_theme(self, theme):
        """Set application theme"""
        try:
            if theme == "light":
                self.style.theme_use('default')
            else:
                theme_path = get_resource_path('forest-dark.tcl')
                if os.path.exists(theme_path):
                    self.root.tk.call('source', theme_path)
                    self.style.theme_use('forest-dark')
            
            # Update theme state
            self.current_theme = theme
            
        except Exception as e:
            logging.error(f"Error setting theme: {e}")
            messagebox.showerror("Theme Error", f"Failed to set theme: {str(e)}")

    def _toggle_theme(self):
        """Toggle between light and dark themes"""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self._set_theme(new_theme)
        self._update_theme_icon()

    def _update_theme_icon(self):
        """Update theme toggle button icon"""
        if hasattr(self, 'theme_button'):
            self.theme_button.configure(
                text="🌞" if self.current_theme == "dark" else "🌙"
            )
        
    def _reset_comparison(self):
        """Reset the comparison tool to initial state"""
        try:
            logging.info("Resetting comparison state")
            
            # Confirm if comparison is running
            if self.comparison_running:
                if not messagebox.askyesno("Reset", "Analysis is in progress. Are you sure you want to reset?"):
                    return
            
            # Clear file paths
            self.ipsw1_path.set("")
            self.ipsw2_path.set("")
            
            # Reset progress and status
            self.progress_var.set(0)
            self.status_var.set("Ready for analysis")
            
            # Reset text widgets
            for widget in [self.summary_text, self.technical_text, self.impact_text]:
                widget.config(state=tk.NORMAL)
                widget.delete(1.0, tk.END)
                widget.config(state=tk.DISABLED)
            
            # Enable compare button if disabled
            self.compare_button.state(['!disabled'])
            
            # Clean up any temporary files
            self._cleanup()
            
            # Reset flags
            self.comparison_running = False
            
            logging.info("Comparison reset completed")
            
        except Exception as e:
            logging.error(f"Error resetting comparison: {e}")
            messagebox.showerror("Error", f"Failed to reset comparison: {str(e)}")

    def _cleanup(self):
        """Clean up temporary files and resources"""
        try:
            logging.info("Starting cleanup")
            
            # Clean up temp directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir, ignore_errors=True)
                    logging.info(f"Cleaned up temp directory: {self.temp_dir}")
                except Exception as e:
                    logging.error(f"Error cleaning temp directory: {e}")
                
                self.temp_dir = None
            
            # Reset any other temporary resources
            if hasattr(self, 'comparison_thread') and self.comparison_thread:
                self.comparison_thread = None
            
            logging.info("Cleanup completed")
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
            # Continue even if cleanup fails

    def _create_temp_directory(self):
        """Create a new temporary directory"""
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="ipsw_analyze_")
            logging.info(f"Created temp directory: {self.temp_dir}")
            return self.temp_dir
        except Exception as e:
            logging.error(f"Error creating temp directory: {e}")
            raise

    def _handle_cleanup_error(self, error):
        """Handle cleanup errors gracefully"""
        logging.error(f"Cleanup error: {error}")
        messagebox.showwarning(
            "Cleanup Warning",
            "Some temporary files could not be removed. They will be cleared on system restart."
        )

    def _reset_ui_state(self):
        """Reset UI elements to initial state"""
        try:
            # Reset progress bar
            self.progress_var.set(0)
            
            # Reset status
            self.status_var.set("Ready for analysis")
            
            # Clear text widgets
            for widget in [self.summary_text, self.technical_text, self.impact_text]:
                widget.config(state=tk.NORMAL)
                widget.delete(1.0, tk.END)
                widget.config(state=tk.DISABLED)
            
            # Reset button states
            self.compare_button.state(['!disabled'])
            
            logging.info("UI state reset completed")
            
        except Exception as e:
            logging.error(f"Error resetting UI state: {e}")
            raise
        
    def _create_progress_section(self, parent):
        """Create progress section"""
        try:
            progress_frame = ttk.LabelFrame(parent, text="Analysis Progress", padding="5")
            progress_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
            
            self.progress_bar = ttk.Progressbar(
                progress_frame,
                variable=self.progress_var,
                maximum=100
            )
            self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
            
            self.status_label = ttk.Label(progress_frame, textvariable=self.status_var)
            self.status_label.grid(row=1, column=0, sticky=tk.W, pady=5)
            
            progress_frame.columnconfigure(0, weight=1)
            
        except Exception as e:
            logging.error(f"Error creating progress section: {e}")
            raise

    def _create_results_section(self, parent):
        """Create results section with notebook tabs"""
        try:
            results_frame = ttk.LabelFrame(parent, text="Analysis Results", padding="5")
            results_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
            
            # Create notebook for tabbed results
            self.results_notebook = ttk.Notebook(results_frame)
            self.results_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # Summary tab
            summary_frame = ttk.Frame(self.results_notebook)
            self.results_notebook.add(summary_frame, text="Summary")
            
            self.summary_text = tk.Text(summary_frame, height=15, wrap=tk.WORD)
            summary_scroll = ttk.Scrollbar(summary_frame, orient=tk.VERTICAL, command=self.summary_text.yview)
            self.summary_text['yscrollcommand'] = summary_scroll.set
            
            self.summary_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            summary_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
            
            # Technical details tab
            tech_frame = ttk.Frame(self.results_notebook)
            self.results_notebook.add(tech_frame, text="Technical Details")
            
            self.technical_text = tk.Text(tech_frame, height=15, wrap=tk.WORD)
            tech_scroll = ttk.Scrollbar(tech_frame, orient=tk.VERTICAL, command=self.technical_text.yview)
            self.technical_text['yscrollcommand'] = tech_scroll.set
            
            self.technical_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            tech_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
            
            # Impact analysis tab
            impact_frame = ttk.Frame(self.results_notebook)
            self.results_notebook.add(impact_frame, text="Impact Analysis")
            
            self.impact_text = tk.Text(impact_frame, height=15, wrap=tk.WORD)
            impact_scroll = ttk.Scrollbar(impact_frame, orient=tk.VERTICAL, command=self.impact_text.yview)
            self.impact_text['yscrollcommand'] = impact_scroll.set
            
            self.impact_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            impact_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
            
            # Configure weights
            results_frame.columnconfigure(0, weight=1)
            results_frame.rowconfigure(0, weight=1)
            for frame in [summary_frame, tech_frame, impact_frame]:
                frame.columnconfigure(0, weight=1)
                frame.rowconfigure(0, weight=1)
                
        except Exception as e:
            logging.error(f"Error creating results section: {e}")
            raise

    def _start_comparison(self):
        """Start the comparison process"""
        if self.comparison_running:
            messagebox.showwarning("Warning", "Analysis already in progress!")
            return
            
        if not self._validate_inputs():
            return
            
        self.comparison_running = True
        self.compare_button.state(['disabled'])
        self.progress_var.set(0)
        
        # Reset text widgets
        for widget in [self.summary_text, self.technical_text, self.impact_text]:
            widget.config(state=tk.NORMAL)
            widget.delete(1.0, tk.END)
            widget.config(state=tk.DISABLED)
        
        # Start analysis in separate thread
        thread = threading.Thread(target=self._run_comparison)
        thread.daemon = True
        thread.start()

    def _run_comparison(self):
        """Run the comparison process"""
        try:
            self._setup_temp_directory()
            self._update_status("Extracting first IPSW file...", 10)
            
            # Extract IPSWs
            self._extract_ipsw(self.ipsw1_path.get(), os.path.join(self.temp_dir, "ipsw1"))
            self._update_status("Extracting second IPSW file...", 30)
            self._extract_ipsw(self.ipsw2_path.get(), os.path.join(self.temp_dir, "ipsw2"))
            
            # Compare files
            self._update_status("Analyzing differences...", 50)
            differences = self._compare_directories()
            
            # Generate analysis
            self._update_status("Generating detailed analysis...", 70)
            analysis = self._generate_detailed_analysis(differences)
            
            # Add AI insights
            self._update_status("Performing AI analysis...", 80)
            ai_insights = self._perform_ai_analysis(differences, analysis)
            analysis['impact'] += "\n\n" + ai_insights
            
            # Show results
            self._update_status("Preparing analysis report...", 90)
            self._show_results(analysis)
            
            self._update_status("Analysis complete!", 100)
            
        except Exception as e:
            logging.error(f"Error in comparison: {str(e)}", exc_info=True)
            self._handle_error(str(e))
        finally:
            self._cleanup()
            self.comparison_running = False
            self.root.after(0, lambda: self.compare_button.state(['!disabled']))

    def _validate_inputs(self):
        """Validate input files"""
        if not self.ipsw1_path.get() or not self.ipsw2_path.get():
            messagebox.showerror("Error", "Please select both IPSW files!")
            return False
            
        if not os.path.exists(self.ipsw1_path.get()) or not os.path.exists(self.ipsw2_path.get()):
            messagebox.showerror("Error", "One or both selected files do not exist!")
            return False
            
        return True

    def _setup_temp_directory(self):
        """Set up temporary directory for extraction"""
        self.temp_dir = tempfile.mkdtemp(prefix="ipsw_analyze_")
        logging.info(f"Created temp directory: {self.temp_dir}")

    def _cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logging.info("Cleaned up temp directory")
            except Exception as e:
                logging.error(f"Error cleaning up temp directory: {str(e)}")
            self.temp_dir = None

    def _extract_ipsw(self, ipsw_path, extract_dir):
        """Extract IPSW file"""
        try:
            with zipfile.ZipFile(ipsw_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            logging.info(f"Extracted IPSW to {extract_dir}")
        except Exception as e:
            logging.error(f"Error extracting IPSW: {str(e)}")
            raise

    def _compare_directories(self):
        """Compare extracted IPSW directories"""
        differences = {
            'added': [],
            'removed': [],
            'modified': [],
            'unchanged': []
        }
        
        try:
            dir1 = os.path.join(self.temp_dir, "ipsw1")
            dir2 = os.path.join(self.temp_dir, "ipsw2")
            
            for root, _, files in os.walk(dir1):
                rel_path = os.path.relpath(root, dir1)
                for file in files:
                    file1_path = os.path.join(root, file)
                    file2_path = os.path.join(dir2, rel_path, file)
                    
                    if os.path.exists(file2_path):
                        if self._files_differ(file1_path, file2_path):
                            differences['modified'].append(os.path.join(rel_path, file))
                        else:
                            differences['unchanged'].append(os.path.join(rel_path, file))
                    else:
                        differences['removed'].append(os.path.join(rel_path, file))
            
            # Check for added files
            for root, _, files in os.walk(dir2):
                rel_path = os.path.relpath(root, dir2)
                for file in files:
                    if not os.path.exists(os.path.join(dir1, rel_path, file)):
                        differences['added'].append(os.path.join(rel_path, file))
                        
            logging.info(f"Found differences: {differences}")
            return differences
            
        except Exception as e:
            logging.error(f"Error comparing directories: {str(e)}")
            raise
    
    def _files_differ(self, file1, file2):
        """Compare two files using SHA-256 hash"""
        try:
            return self._get_file_hash(file1) != self._get_file_hash(file2)
        except Exception as e:
            logging.error(f"Error comparing files: {str(e)}")
            raise
    
    def _browse_file(self, path_var):
        """Open file browser dialog for IPSW selection"""
        try:
            logging.info("Opening file browser")
            initial_dir = os.path.expanduser("~")  # Start in user's home directory
            
            filename = filedialog.askopenfilename(
                title="Select IPSW File",
                initialdir=initial_dir,
                filetypes=[
                    ("IPSW files", "*.ipsw"),
                    ("All files", "*.*")
                ],
                parent=self.root  # Ensure dialog is modal to main window
            )
            
            if filename:
                logging.info(f"Selected file: {filename}")
                path_var.set(filename)
                
                # Validate file
                if not os.path.exists(filename):
                    raise FileNotFoundError(f"Selected file does not exist: {filename}")
                    
                # Check file extension
                if not filename.lower().endswith('.ipsw'):
                    messagebox.showwarning(
                        "File Type Warning",
                        "Selected file is not an .ipsw file. Analysis may fail."
                    )
                
            else:
                logging.info("File selection cancelled")
                
        except Exception as e:
            logging.error(f"Error in file selection: {e}")
            messagebox.showerror(
                "File Selection Error",
                f"Failed to select file: {str(e)}"
            )

    def _validate_file_selection(self):
        """Validate the selected IPSW files"""
        try:
            # Check if both files are selected
            if not self.ipsw1_path.get() or not self.ipsw2_path.get():
                messagebox.showerror("Error", "Please select both IPSW files!")
                return False
            
            # Check if files exist
            if not os.path.exists(self.ipsw1_path.get()):
                messagebox.showerror("Error", "First IPSW file does not exist!")
                return False
                
            if not os.path.exists(self.ipsw2_path.get()):
                messagebox.showerror("Error", "Second IPSW file does not exist!")
                return False
            
            # Check if files are different
            if self.ipsw1_path.get() == self.ipsw2_path.get():
                messagebox.showerror("Error", "Please select different IPSW files!")
                return False
            
            # Check file sizes
            size1 = os.path.getsize(self.ipsw1_path.get())
            size2 = os.path.getsize(self.ipsw2_path.get())
            
            if size1 == 0 or size2 == 0:
                messagebox.showerror("Error", "One or both IPSW files are empty!")
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"Error validating file selection: {e}")
            messagebox.showerror("Error", f"Failed to validate files: {str(e)}")
            return False

    def _get_file_info(self, filepath):
        """Get information about selected file"""
        try:
            info = {
                'size': os.path.getsize(filepath),
                'modified': datetime.fromtimestamp(os.path.getmtime(filepath)),
                'created': datetime.fromtimestamp(os.path.getctime(filepath)),
                'is_valid': filepath.lower().endswith('.ipsw')
            }
            return info
        except Exception as e:
            logging.error(f"Error getting file info: {e}")
            return None
        
    def _get_file_hash(self, filepath):
        """Calculate SHA-256 hash of a file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logging.error(f"Error calculating file hash: {str(e)}")
            raise

    def _analyze_component(self, filename):
        """Analyze a component based on its filename"""
        analysis = {
            'component_type': 'unknown',
            'description': '',
            'impact': {}
        }
        
        # Extract component type from filename
        for component_type in self.component_knowledge.keys():
            if component_type.lower() in filename.lower():
                analysis['component_type'] = component_type
                analysis.update(self.component_knowledge[component_type])
                break
        
        # Additional analysis based on filename patterns
        if 'dmg.trustcache' in filename:
            analysis['description'] = 'Trust cache component containing security certificates and trust data'
            analysis['impact']['security'] = 'Updates to system security certificates and trust relationships'
        elif '.root_hash' in filename:
            analysis['description'] = 'Root hash for system integrity verification'
            analysis['impact']['security'] = 'Changes to system integrity verification mechanism'
        elif '.plist' in filename:
            analysis['description'] = 'System configuration file'
            analysis['impact']['configuration'] = 'Changes to system settings and configurations'
        
        return analysis

    def _perform_ai_analysis(self, differences, basic_analysis):
        """Perform AI-enhanced analysis of the changes"""
        insights = []
        
        try:
            # Analyze change patterns
            modified_files = differences['modified']
            total_changes = len(modified_files)
            
            # Initialize counters for different types of changes
            change_types = defaultdict(int)
            
            # Pattern matching for different types of changes
            for file in modified_files:
                file_lower = file.lower()
                
                # Check against each pattern type
                for category, info in self.ai_knowledge_base['system_patterns'].items():
                    for pattern in info['patterns']:
                        if re.search(pattern, file_lower):
                            change_types[category] += 1
                            break
            
            # Generate insights
            insights.append("\n=== AI-Enhanced Analysis ===\n")
            
            # Overall change assessment
            if total_changes > self.ai_knowledge_base['change_patterns']['large_scale']['threshold']:
                insights.append(self.ai_knowledge_base['change_patterns']['large_scale']['explanation'])
            
            # Analyze component interactions
            component_changes = set()
            for file in modified_files:
                for component in self.component_knowledge.keys():
                    if component.lower() in file.lower():
                        component_changes.add(component)
            
            # Check for significant component interactions
            for interaction, details in self.ai_knowledge_base['component_interactions'].items():
                components = interaction.split(' + ')
                if all(comp in component_changes for comp in components):
                    insights.append(f"\nSignificant Interaction Detected:")
                    insights.append(f"- Impact: {details['impact']}")
                    insights.append(f"- Recommendation: {details['recommendation']}")
            
            # Generate category-specific insights
            for category, count in change_types.items():
                if count > 0:
                    insights.append(f"\n{category.title()} Analysis:")
                    insights.append(self.ai_knowledge_base['system_patterns'][category]['explanation'])
                    insights.append(f"Number of affected components: {count}")
            
            # Additional behavioral analysis
            insights.append("\nBehavioral Impact Analysis:")
            if change_types['security'] > 0:
                insights.append("• This update includes security improvements that may require re-authentication.")
            if change_types['performance'] > 0:
                insights.append("• Users may notice changes in system responsiveness and app launch times.")
            if change_types['features'] > 0:
                insights.append("• New system capabilities may become available after this update.")
            
            # Add recommendations
            insights.append("\nIntelligent Recommendations:")
            priority_level = "High" if change_types['security'] > 2 else \
                           "Medium" if total_changes > 10 else "Low"
            insights.append(f"• Update Priority: {priority_level}")
            
            if change_types['security'] > 0:
                insights.append("• Backup your device before updating due to security changes")
            if change_types['performance'] > 0:
                insights.append("• Monitor device performance after update for any significant changes")
            
            return "\n".join(insights)
            
        except Exception as e:
            logging.error(f"Error in AI analysis: {str(e)}", exc_info=True)
            return "AI analysis failed: See technical details for more information."

    #about and documentation
    def _create_footer(self, parent):
        """Create footer with version info and links"""
        try:
            footer_frame = ttk.Frame(parent, padding="5")
            footer_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
            
            
            separator = ttk.Separator(parent, orient='horizontal')
            separator.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
            
            
            about_btn = ttk.Button(
                footer_frame,
                text="About",
                command=self._show_about,
                style='Footer.TButton'
            )
            about_btn.pack(side=tk.LEFT, padx=5)
            
            doc_btn = ttk.Button(
                footer_frame,
                text="Documentation",
                command=self._show_documentation,
                style='Footer.TButton'
            )
            doc_btn.pack(side=tk.LEFT, padx=5)
            
            # Add version info
            version_label = ttk.Label(
                footer_frame,
                text=f"v{self.current_version}",
                style='Footer.TLabel'
            )
            version_label.pack(side=tk.RIGHT, padx=5)
            
            # Add status message area
            self.status_message = ttk.Label(
                footer_frame,
                text="Ready",
                padding=(5, 2)
            )
            self.status_message.pack(side=tk.RIGHT, padx=20)
            
            # Configure footer styles
            self.style.configure('Footer.TButton', font=('Helvetica', 9))
            self.style.configure('Footer.TLabel', font=('Helvetica', 9))
            
            return footer_frame
            
        except Exception as e:
            logging.error(f"Error creating footer: {e}")
            raise

    def _show_about(self):
        """Show about dialog"""
        try:
            about_window = tk.Toplevel(self.root)
            about_window.title("About IPSW Firmware Comparison Tool")
            about_window.geometry("400x500")
            
            # Make window modal
            about_window.transient(self.root)
            about_window.grab_set()
            
            # Add icon if available
            if hasattr(self, 'logo_about'):
                logo_label = ttk.Label(about_window, image=self.logo_about)
                logo_label.pack(pady=(20, 15))
            
            # Title
            title_label = ttk.Label(
                about_window,
                text="IPSW Firmware Comparison Tool",
                font=('Helvetica', 14, 'bold')
            )
            title_label.pack(pady=(0, 10))
            
            # Version
            version_label = ttk.Label(
                about_window,
                text=f"Version {self.current_version}",
                font=('Helvetica', 10)
            )
            version_label.pack()
            
            # Description
            desc_text = """A sophisticated tool created by Sam for analyzing and comparing iOS firmware files.
            
This tool provides detailed analysis of changes between firmware versions and their potential impact on device functionality.

Key Features:
• Detailed component analysis
• Security impact assessment
• Performance change detection
• AI-enhanced analysis
• Export capabilities"""
            
            desc_label = ttk.Label(
                about_window,
                text=desc_text,
                wraplength=300,
                justify=tk.LEFT
            )
            desc_label.pack(pady=20, padx=20)
            
            # Copyright
            copyright_label = ttk.Label(
                about_window,
                text="Copyright © 2024"
            )
            copyright_label.pack(pady=(10,0))
            
            # Close button
            close_btn = ttk.Button(
                about_window,
                text="Close",
                command=about_window.destroy
            )
            close_btn.pack(pady=20)
            
        except Exception as e:
            logging.error(f"Error showing about dialog: {e}")
            raise

    def _show_documentation(self):
        """Show documentation window"""
        try:
            doc_window = tk.Toplevel(self.root)
            doc_window.title("Documentation - IPSW Firmware Comparison Tool")
            doc_window.geometry("800x600")
            
            # Make window modal
            doc_window.transient(self.root)
            doc_window.grab_set()
            
            # Create notebook for tabbed documentation
            doc_notebook = ttk.Notebook(doc_window)
            doc_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Getting Started tab
            getting_started = ttk.Frame(doc_notebook, padding="10")
            doc_notebook.add(getting_started, text="Getting Started")
            
            ttk.Label(
                getting_started,
                text="Getting Started",
                font=('Helvetica', 12, 'bold')
            ).pack(anchor=tk.W)
            
            steps = [
                "1. Select two IPSW files using the browse buttons",
                "2. Click 'Analyze Firmware Files' to begin analysis",
                "3. Wait for the analysis to complete",
                "4. Review the results in the different tabs",
                "5. Export the analysis if needed"
            ]
            
            for step in steps:
                ttk.Label(
                    getting_started,
                    text=step,
                    wraplength=700
                ).pack(anchor=tk.W, pady=2)
            
            # Features tab
            features = ttk.Frame(doc_notebook, padding="10")
            doc_notebook.add(features, text="Features")
            
            ttk.Label(
                features,
                text="Key Features",
                font=('Helvetica', 12, 'bold')
            ).pack(anchor=tk.W)
            
            features_list = [
                "• Detailed component analysis",
                "• Security impact assessment",
                "• Performance change detection",
                "• AI-enhanced analysis",
                "• Multiple export formats",
                "• Comprehensive logging"
            ]
            
            for feature in features_list:
                ttk.Label(
                    features,
                    text=feature,
                    wraplength=700
                ).pack(anchor=tk.W, pady=2)
            
            # Close button
            close_btn = ttk.Button(
                doc_window,
                text="Close",
                command=doc_window.destroy
            )
            close_btn.pack(pady=10)
            
        except Exception as e:
            logging.error(f"Error showing documentation: {e}")
            raise
        
    def _export_analysis(self):
        """Export analysis results to file"""
        if not hasattr(self, 'summary_text') or not self.summary_text.get(1.0, tk.END).strip():
            messagebox.showwarning("Warning", "No analysis results to export!")
            return
            
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("JSON files", "*.json"),
                    ("HTML files", "*.html"),
                    ("All files", "*.*")
                ],
                title="Export Analysis Report"
            )
            
            if filename:
                file_ext = os.path.splitext(filename)[1].lower()
                
                if file_ext == '.json':
                    self._export_json(filename)
                elif file_ext == '.html':
                    self._export_html(filename)
                else:
                    self._export_text(filename)
                    
                messagebox.showinfo("Success", "Analysis report exported successfully!")
                
        except Exception as e:
            logging.error(f"Error exporting analysis: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Failed to export analysis: {str(e)}")

    def _generate_detailed_analysis(self, differences):
        """Generate detailed analysis with sophisticated insights"""
        summary = []
        technical = []
        impact = []

        # Get file paths for analysis
        first_ipsw = os.path.basename(self.ipsw1_path.get())
        second_ipsw = os.path.basename(self.ipsw2_path.get())
        
        # Extract versions from filenames (assuming format includes version number)
        version1 = re.search(r'(\d+\.\d+[._]\d+)', first_ipsw)
        version2 = re.search(r'(\d+\.\d+[._]\d+)', second_ipsw)
        version_str = f"Version {version1.group(1) if version1 else 'Unknown'} → {version2.group(1) if version2 else 'Unknown'}"
        
        # Summary section
        summary.append("=== IPSW Firmware Update Analysis ===\n")
        summary.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary.append(f"Firmware Comparison: {version_str}\n")
        summary.append("Key Findings:")
        
        # Initialize change counters
        change_stats = {
            'security': 0,
            'performance': 0,
            'feature': 0,
            'boot': 0,
            'system': 0,
            'critical': 0
        }
        
        # Component classification patterns
        component_patterns = {
            'security': [
                r'.*trustcache.*',
                r'.*seal.*',
                r'.*crypto.*',
                r'.*security.*',
                r'.*certificate.*',
                r'.*keychain.*',
                r'.*auth.*'
            ],
            'performance': [
                r'.*kernel.*',
                r'.*cache.*',
                r'.*dyld.*',
                r'.*perf.*',
                r'.*memory.*'
            ],
            'boot': [
                r'.*iboot.*',
                r'.*boot.*',
                r'.*ibss.*',
                r'.*ibec.*'
            ],
            'system': [
                r'.*system.*',
                r'.*framework.*',
                r'.*daemon.*',
                r'.*service.*'
            ],
            'critical': [
                r'.*kernelcache.*',
                r'.*sep.*',
                r'.*baseband.*'
            ]
        }
        
        # Analyze modified components
        critical_components = []
        security_components = []
        system_changes = []
        
        for file in differences['modified']:
            file_lower = file.lower()
            component_analyzed = False
            
            # Analyze file against patterns
            for category, patterns in component_patterns.items():
                for pattern in patterns:
                    if re.match(pattern, file_lower):
                        change_stats[category] += 1
                        component_analyzed = True
                        
                        # Track critical changes
                        if category == 'critical':
                            critical_components.append(file)
                        elif category == 'security':
                            security_components.append(file)
                        elif category == 'system':
                            system_changes.append(file)
                        
                        # Get component analysis
                        analysis = self._analyze_component(file)
                        
                        # Add to technical details
                        technical.append(f"\nComponent: {file}")
                        technical.append(f"Category: {category.upper()}")
                        if analysis['description']:
                            technical.append(f"Description: {analysis['description']}")
                        
                        # Add impacts
                        if analysis['impact']:
                            impact.append(f"\n{file}:")
                            for impact_type, impact_desc in analysis['impact'].items():
                                impact.append(f"- {impact_type.title()}: {impact_desc}")
        
        # Generate high-level summary based on changes
        if critical_components:
            summary.append("\nCritical System Changes Detected:")
            for comp in critical_components:
                summary.append(f"- {comp}")
            summary.append("  These changes affect core system functionality and security")
        
        if security_components:
            summary.append("\nSecurity-Related Modifications:")
            summary.append(f"- {len(security_components)} security components modified")
            summary.append("- Updates include security patches and trust mechanism changes")
        
        if change_stats['boot'] > 0:
            summary.append("\nBoot System Changes:")
            summary.append("- Modified boot chain components detected")
            summary.append("- May affect device startup and security verification")
        
        # Add statistics
        summary.append("\nChange Statistics:")
        summary.append(f"- Security Changes: {change_stats['security']}")
        summary.append(f"- Performance Changes: {change_stats['performance']}")
        summary.append(f"- Boot System Changes: {change_stats['boot']}")
        summary.append(f"- System Components: {change_stats['system']}")
        summary.append(f"- Critical Components: {change_stats['critical']}")
        
        # Overall statistics
        summary.append(f"\nTotal Changes:")
        summary.append(f"- Added files: {len(differences['added'])}")
        summary.append(f"- Removed files: {len(differences['removed'])}")
        summary.append(f"- Modified files: {len(differences['modified'])}")
        summary.append(f"- Unchanged files: {len(differences['unchanged'])}")
        
        # Generate update priority and recommendations
        summary.append("\nUpdate Analysis:")
        priority = "HIGH" if change_stats['critical'] > 0 or change_stats['security'] > 2 else \
                  "MEDIUM" if change_stats['security'] > 0 or change_stats['performance'] > 2 else \
                  "LOW"
        summary.append(f"Update Priority: {priority}")
        
        # Add recommendations
        summary.append("\nRecommendations:")
        if change_stats['critical'] > 0:
            summary.append("✓ Critical system update - install as soon as possible")
        if change_stats['security'] > 0:
            summary.append("✓ Contains important security improvements")
        if change_stats['performance'] > 0:
            summary.append("✓ Performance improvements included")
        if change_stats['boot'] > 0:
            summary.append("✓ Backup device before updating due to boot system changes")
        
        # Add compatibility notes
        if system_changes:
            summary.append("\nCompatibility Notes:")
            summary.append("- This update modifies core system components")
            summary.append("- May require fresh system boot after installation")
            if change_stats['critical'] > 0:
                summary.append("- Could affect third-party app compatibility")
        
        return {
            'summary': "\n".join(summary),
            'technical': "\n".join(technical),
            'impact': "\n".join(impact)
        }
        
    def _check_updates(self):
        """Check for software updates"""
        try:
            self.status_var.set("Checking for updates...")
            response = requests.get(f"https://api.github.com/repos/{self.github_repo}/releases/latest")
            
            if response.status_code == 200:
                latest_version = response.json()['tag_name'].replace('v', '')
                if latest_version > self.current_version:
                    if messagebox.askyesno("Update Available", 
                                         f"Version {latest_version} is available. Would you like to download it?"):
                        webbrowser.open(response.json()['html_url'])
                else:
                    messagebox.showinfo("Up to Date", 
                                      f"You are running the latest version ({self.current_version})")
            else:
                raise Exception(f"Failed to check for updates: {response.status_code}")
                
        except Exception as e:
            logging.error(f"Error checking updates: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Failed to check for updates: {str(e)}")
        finally:
            self.status_var.set("Ready")

    def _show_results(self, analysis):
        """Display analysis results in the UI"""
        try:
            def update_text():
                for widget, content in [
                    (self.summary_text, analysis['summary']),
                    (self.technical_text, analysis['technical']),
                    (self.impact_text, analysis['impact'])
                ]:
                    widget.config(state=tk.NORMAL)
                    widget.delete(1.0, tk.END)
                    widget.insert(tk.END, content)
                    widget.config(state=tk.DISABLED)
                    
            self.root.after(0, update_text)
            
        except Exception as e:
            logging.error(f"Error showing results: {str(e)}")
            raise

    def _update_status(self, message, progress):
        """Update status message and progress bar"""
        try:
            self.root.after(0, lambda: self.status_var.set(message))
            self.root.after(0, lambda: self.progress_var.set(progress))
        except Exception as e:
            logging.error(f"Error updating status: {str(e)}")

    def _handle_error(self, error_message):
        """Handle and display errors"""
        logging.error(f"Error occurred: {error_message}")
        self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {error_message}"))
        self._update_status("Error occurred", 0)

def main():
    try:
        logging.info("Starting application")
        root = tk.Tk()
        app = IPSWComparerGUI(root)
        
        def on_closing():
            try:
                if app.comparison_running:
                    if not messagebox.askyesno("Quit", "Analysis is in progress. Are you sure you want to quit?"):
                        return
                app._cleanup()
                root.destroy()
            except Exception as e:
                logging.error(f"Error during shutdown: {str(e)}", exc_info=True)
                root.destroy()
                
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        logging.info("Starting main loop")
        root.mainloop()
        
    except Exception as e:
        logging.critical("Fatal error in main application", exc_info=True)
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Fatal Error", 
                               f"Application failed to start\n\nError: {str(e)}\n\n"
                               f"Check log file: {log_file}")
            root.destroy()
        except:
            print(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()