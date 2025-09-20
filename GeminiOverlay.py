import customtkinter as ctk
import keyboard
import threading
import tkinter as tk
from tkinter import messagebox
import google.generativeai as genai
import os
import json
import time
from datetime import datetime

class GeminiEverywhere:
    def __init__(self):
        # Configure CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Initialize variables
        self.window = None
        self.is_visible = False
        self.chat_history = []
        self.hotkey_thread = None
        self.running = True
        self.current_mode = "Normal"  # Default mode
        self.current_model = "gemini-2.5-flash"  # Default model
        self.pinned_context = []  # For context pinning
        
        # Available models
        self.available_models = {
            "Gemini 2.5 Flash": "gemini-2.5-flash",
            "Gemini 2.5 Pro": "gemini-2.5-pro"
        }
        
        # Initialize Gemini API
        self.api_key = self.load_api_key()
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-pro')
            except Exception as e:
                print(f"Error configuring Gemini: {e}")
                self.model = None
        else:
            self.model = None
        
        # Load chat history
        self.load_history()
        
        # Create the main window immediately
        self.create_window()
        
        # Setup global hotkey in a separate thread
        self.setup_hotkey()
    
    def get_mode_prompts(self):
        """Define different conversation modes with system prompts"""
        return {
            "Normal": {
                "name": "🤖 Normal",
                "prompt": "You are a helpful AI assistant. Provide clear, accurate, and helpful responses."
            },
            "Informal": {
                "name": "😎 Informal", 
                "prompt": "You are a casual, friendly AI assistant. Use informal language, contractions, and speak like you're chatting with a friend. Be relaxed and conversational."
            },
            "Professional": {
                "name": "👔 Professional",
                "prompt": "You are a professional AI assistant. Use formal language, proper grammar, and maintain a business-appropriate tone. Be thorough and precise in your responses."
            },
            "Creative": {
                "name": "🎨 Creative",
                "prompt": "You are a creative AI assistant. Be imaginative, think outside the box, and provide creative solutions. Use vivid language and interesting analogies."
            },
            "Teacher": {
                "name": "📚 Teacher",
                "prompt": "You are an educational AI tutor. Break down complex topics into easy-to-understand explanations. Use examples, analogies, and step-by-step guidance."
            },
            "Coder": {
                "name": "💻 Coder",
                "prompt": "You are a programming expert. Focus on code quality, best practices, and clear technical explanations. Provide working code examples and explain your reasoning."
            },
            "Concise": {
                "name": "⚡ Concise",
                "prompt": "You are a concise AI assistant. Give brief, to-the-point answers. Avoid lengthy explanations unless specifically requested. Be direct and efficient."
            },
            "Analyzer": {
                "name": "🔍 Analyzer",
                "prompt": "You are an analytical AI assistant. Approach problems systematically, break them down into components, and provide detailed analysis with pros/cons."
            },
            "Brainstormer": {
                "name": "💡 Brainstormer",
                "prompt": "You are a brainstorming partner. Generate multiple ideas, think creatively, and help explore different possibilities. Encourage innovative thinking."
            }
        }
    
    def get_quick_commands(self):
        """Returns a dictionary of quick commands and their descriptions."""
        return {
            '/summarize': "Get a concise summary of the following text.",
            '/translate': "Translate text to English (or Spanish if English).",
            '/explain': "Explain a topic in simple, easy-to-understand terms.",
            '/improve': "Improve and rewrite the provided text for clarity and style.",
            '/code': "Review a piece of code and suggest improvements or best practices.",
            '/fix': "Identify and fix any errors or bugs in the provided code.",
            '/ideas': "Brainstorm creative ideas related to a given topic.",
            '/pros': "List the pros and cons for a given subject."
        }
        
    def apply_mode_to_query(self, query):
        """Apply the current mode's system prompt to the user's query"""
        # Handle quick commands
        if query.startswith('/'):
            return self.handle_quick_command(query)
        
        # Apply pinned context
        context_text = ""
        if self.pinned_context:
            context_text = "\n\nPinned Context:\n" + "\n".join([f"- {item}" for item in self.pinned_context]) + "\n"
        
        modes = self.get_mode_prompts()
        if self.current_mode in modes:
            mode_prompt = modes[self.current_mode]["prompt"]
            return f"System: {mode_prompt}{context_text}\n\nUser: {query}"
        return query
    
    def handle_quick_command(self, query):
        """Handle quick commands like /summarize, /translate, etc."""
        command = query.split()[0].lower()
        content = query[len(command):].strip()
        
        # This dictionary defines the final prompt sent to the API for each command
        command_prompts = {
            '/summarize': f"Please provide a concise summary of the following:\n\n{content}",
            '/translate': f"Please translate the following text to English (or if it's already English, translate to Spanish):\n\n{content}",
            '/explain': f"Please explain the following in simple terms:\n\n{content}",
            '/improve': f"Please improve and rewrite the following text:\n\n{content}",
            '/code': f"Please review this code and suggest improvements:\n\n{content}",
            '/fix': f"Please identify and fix any issues in this code:\n\n{content}",
            '/ideas': f"Please brainstorm creative ideas related to:\n\n{content}",
            '/pros': f"Please list the pros and cons of:\n\n{content}"
        }
        
        if command in command_prompts:
            if content:
                return command_prompts[command]
            else:
                # Return a user-friendly error if no content is provided
                return f"Please provide content after the {command} command. For example: {command} your text here"
        
        return query  # If not a recognized command, return the original query
    
    def load_api_key(self):
        """Load API key from file or environment variable"""
        try:
            if os.path.exists('gemini_api_key.txt'):
                with open('gemini_api_key.txt', 'r') as f:
                    key = f.read().strip()
                    if key:
                        return key
        except Exception as e:
            print(f"Error loading API key from file: {e}")
        
        # Try environment variable
        env_key = os.getenv('GEMINI_API_KEY')
        if env_key:
            return env_key
            
        return None
    
    def save_api_key(self, api_key):
        """Save API key to file"""
        try:
            with open('gemini_api_key.txt', 'w') as f:
                f.write(api_key)
            return True
        except Exception as e:
            print(f"Error saving API key: {e}")
            return False
    
    def load_history(self):
        """Load chat history from file"""
        try:
            if os.path.exists('gemini_history.json'):
                with open('gemini_history.json', 'r', encoding='utf-8') as f:
                    self.chat_history = json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
            self.chat_history = []
    
    def save_history(self):
        """Save chat history to file"""
        try:
            # Keep only last 50 messages to prevent file from getting too large
            if len(self.chat_history) > 50:
                self.chat_history = self.chat_history[-50:]
            
            with open('gemini_history.json', 'w', encoding='utf-8') as f:
                json.dump(self.chat_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def setup_hotkey(self):
        """Setup global hotkey listener in a separate thread"""
        def hotkey_listener():
            try:
                keyboard.add_hotkey('ctrl+space', self.toggle_window_safe)
                print("✅ Hotkey Ctrl+Space registered successfully!")
            except Exception as e:
                print(f"❌ Error setting up hotkey: {e}")
                print("You can still use the window manually.")
        
        self.hotkey_thread = threading.Thread(target=hotkey_listener, daemon=True)
        self.hotkey_thread.start()
    
    def toggle_window_safe(self):
        """Thread-safe window toggle"""
        if self.window:
            self.window.after(0, self.toggle_window)
    
    def create_window(self):
        """Create the main overlay window"""
        self.window = ctk.CTk()
        self.window.title("Gemini Everywhere")
        self.window.geometry("650x550")
        
        # Make window always on top and hide initially
        self.window.attributes('-topmost', True)
        self.window.withdraw()  # Start hidden
        
        # Center window on screen
        self.center_window()
        
        # Configure grid
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(1, weight=1)
        
        # Title and close button frame
        title_frame = ctk.CTkFrame(self.window)
        title_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        title_frame.grid_columnconfigure(0, weight=1)
        
        title_label = ctk.CTkLabel(title_frame, text="🤖 Gemini Everywhere", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, sticky="w", padx=10, pady=8)
        
        # Mode selector dropdown
        modes = self.get_mode_prompts()
        mode_names = [modes[key]["name"] for key in modes.keys()]
        
        self.mode_selector = ctk.CTkOptionMenu(
            title_frame, 
            values=mode_names,
            command=self.on_mode_change,
            width=100,
            font=("Arial", 11)
        )
        self.mode_selector.grid(row=0, column=1, padx=3, pady=8)
        self.mode_selector.set(modes[self.current_mode]["name"])
        
        # Model selector dropdown
        model_names = list(self.available_models.keys())
        self.model_selector = ctk.CTkOptionMenu(
            title_frame,
            values=model_names,
            command=self.on_model_change,
            width=100,
            font=("Arial", 11)
        )
        self.model_selector.grid(row=0, column=2, padx=3, pady=8)
        # Set current model display name
        for name, model_id in self.available_models.items():
            if model_id == self.current_model:
                self.model_selector.set(name)
                break
        
        # Status indicator
        self.status_label = ctk.CTkLabel(title_frame, text="")
        self.status_label.grid(row=0, column=3, padx=3, pady=8)
        self.update_status()
        
        close_btn = ctk.CTkButton(title_frame, text="✕", width=30, height=30, command=self.hide_window)
        close_btn.grid(row=0, column=4, padx=10, pady=8)
        
        # Chat display area
        self.chat_display = ctk.CTkTextbox(self.window, wrap="word", font=("Arial", 12))
        self.chat_display.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # Input frame
        input_frame = ctk.CTkFrame(self.window)
        input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        input_frame.grid_columnconfigure(0, weight=1)
        
        # Query input
        self.query_entry = ctk.CTkEntry(input_frame, placeholder_text="Ask Gemini anything... (Press Enter to send)")
        self.query_entry.grid(row=0, column=0, sticky="ew", padx=(5, 5), pady=8)
        self.query_entry.bind("<Return>", self.send_query)
        self.query_entry.bind("<Control-Return>", lambda e: self.query_entry.insert("end", "\n"))
        
        # Send button
        self.send_btn = ctk.CTkButton(input_frame, text="Send", width=80, command=self.send_query)
        self.send_btn.grid(row=0, column=1, padx=(5, 5), pady=8)
        
        # Control buttons frame
        control_frame = ctk.CTkFrame(self.window)
        control_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 10))
        
        clear_btn = ctk.CTkButton(control_frame, text="Clear", command=self.clear_history, height=32, width=60)
        clear_btn.pack(side="left", padx=3, pady=8)
        
        pin_btn = ctk.CTkButton(control_frame, text="Pin Context", command=self.show_pin_dialog, height=32, width=80)
        pin_btn.pack(side="left", padx=3, pady=8)
        
        copy_btn = ctk.CTkButton(control_frame, text="Copy Last", command=self.copy_last_response, height=32, width=70)
        copy_btn.pack(side="left", padx=3, pady=8)
        
        settings_btn = ctk.CTkButton(control_frame, text="API Key", command=self.show_api_key_dialog, height=32, width=60)
        settings_btn.pack(side="left", padx=3, pady=8)
        
        # Info button
        info_btn = ctk.CTkButton(control_frame, text="Help", command=self.show_help, height=32, width=50)
        info_btn.pack(side="right", padx=3, pady=8)

        # *** NEW: Commands Button ***
        commands_btn = ctk.CTkButton(control_frame, text="Commands", command=self.show_commands_dialog, height=32, width=80)
        commands_btn.pack(side="right", padx=3, pady=8)
        
        # Load and display chat history
        self.refresh_chat_display()
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        print("✅ Window created successfully!")
    
    def show_commands_dialog(self):
        """Show a dialog with a list of available quick commands."""
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("Quick Commands")
        dialog.geometry("550x450")
        dialog.attributes('-topmost', True)
        dialog.transient(self.window)
        dialog.grab_set()

        instructions = ctk.CTkLabel(
            dialog,
            text="🚀 Click a command to insert it into the input box.",
            font=("Arial", 14)
        )
        instructions.pack(pady=15)

        scrollable_frame = ctk.CTkScrollableFrame(dialog)
        scrollable_frame.pack(fill="both", expand=True, padx=15, pady=10)

        commands = self.get_quick_commands()

        for command, description in commands.items():
            command_frame = ctk.CTkFrame(scrollable_frame)
            command_frame.pack(fill="x", pady=5, padx=5)
            command_frame.grid_columnconfigure(1, weight=1)

            btn = ctk.CTkButton(
                command_frame,
                text=command,
                width=100,
                command=lambda cmd=command: self.insert_command_and_focus(cmd, dialog)
            )
            btn.grid(row=0, column=0, padx=10, pady=10)

            desc_label = ctk.CTkLabel(
                command_frame,
                text=description,
                wraplength=350,
                justify="left",
                anchor="w"
            )
            desc_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        close_btn = ctk.CTkButton(dialog, text="Close", command=dialog.destroy)
        close_btn.pack(pady=15)

    def insert_command_and_focus(self, command, dialog):
        """Inserts the command, closes the dialog, and focuses the main window."""
        self.query_entry.delete(0, 'end')
        self.query_entry.insert(0, f"{command} ")
        self.show_window()  # Ensure main window is visible and focused
        dialog.destroy()
        
    def on_model_change(self, selected_model_name):
        """Handle model change from dropdown"""
        if selected_model_name in self.available_models:
            self.current_model = self.available_models[selected_model_name]
            if self.api_key:
                try:
                    self.model = genai.GenerativeModel(self.current_model)
                    print(f"Model changed to: {selected_model_name}")
                except Exception as e:
                    print(f"Error switching model: {e}")
    
    def copy_last_response(self):
        """Copy the last AI response to clipboard"""
        for entry in reversed(self.chat_history):
            if entry["type"] == "assistant" and "Error:" not in entry["content"]:
                try:
                    import pyperclip
                    pyperclip.copy(entry["content"])
                    print("Last response copied to clipboard!")
                    return
                except ImportError:
                    # Fallback to tkinter clipboard
                    self.window.clipboard_clear()
                    self.window.clipboard_append(entry["content"])
                    self.window.update()
                    print("Last response copied to clipboard!")
                    return
        print("No response to copy")
    
    def show_pin_dialog(self):
        """Show dialog to manage pinned context"""
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("Manage Pinned Context")
        dialog.geometry("500x400")
        dialog.attributes('-topmost', True)
        dialog.transient(self.window)
        dialog.grab_set()
        
        # Instructions
        instructions = ctk.CTkLabel(
            dialog,
            text="📌 Pinned context stays active for all queries until removed",
            font=("Arial", 12)
        )
        instructions.pack(pady=10)
        
        # Current pinned items
        if self.pinned_context:
            current_frame = ctk.CTkFrame(dialog)
            current_frame.pack(fill="x", padx=20, pady=10)
            
            ctk.CTkLabel(current_frame, text="Currently Pinned:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=5)
            
            for i, item in enumerate(self.pinned_context):
                item_frame = ctk.CTkFrame(current_frame)
                item_frame.pack(fill="x", padx=10, pady=2)
                
                item_label = ctk.CTkLabel(item_frame, text=f"• {item[:60]}{'...' if len(item) > 60 else ''}", wraplength=300)
                item_label.pack(side="left", padx=10, pady=5)
                
                remove_btn = ctk.CTkButton(item_frame, text="Remove", width=60, height=25, 
                                         command=lambda idx=i: self.remove_pinned_item(idx, dialog))
                remove_btn.pack(side="right", padx=10, pady=5)
        
        # Add new item
        add_frame = ctk.CTkFrame(dialog)
        add_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(add_frame, text="Add New Context:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        
        new_context_entry = ctk.CTkTextbox(add_frame, height=80)
        new_context_entry.pack(fill="x", padx=10, pady=5)
        
        def add_context():
            text = new_context_entry.get("1.0", "end").strip()
            if text:
                self.pinned_context.append(text)
                dialog.destroy()
                print(f"Added pinned context: {text[:50]}...")
        
        button_frame = ctk.CTkFrame(dialog)
        button_frame.pack(pady=20)
        
        add_btn = ctk.CTkButton(button_frame, text="Add Context", command=add_context)
        add_btn.pack(side="left", padx=5)
        
        clear_all_btn = ctk.CTkButton(button_frame, text="Clear All", command=lambda: self.clear_all_pinned(dialog))
        clear_all_btn.pack(side="left", padx=5)
        
        close_btn = ctk.CTkButton(button_frame, text="Close", command=dialog.destroy)
        close_btn.pack(side="left", padx=5)
    
    def remove_pinned_item(self, index, dialog):
        """Remove a pinned context item"""
        if 0 <= index < len(self.pinned_context):
            removed = self.pinned_context.pop(index)
            print(f"Removed pinned context: {removed[:50]}...")
            dialog.destroy()
            self.show_pin_dialog()  # Refresh the dialog
    
    def clear_all_pinned(self, dialog):
        """Clear all pinned context"""
        self.pinned_context = []
        print("Cleared all pinned context")
        dialog.destroy()
    
    def on_mode_change(self, selected_mode_name):
        """Handle mode change from dropdown"""
        modes = self.get_mode_prompts()
        # Find the mode key from the display name
        for key, value in modes.items():
            if value["name"] == selected_mode_name:
                self.current_mode = key
                print(f"Mode changed to: {selected_mode_name}")
                break
    
    def update_status(self):
        """Update the status indicator"""
        if self.model:
            self.status_label.configure(text="🟢 Connected", text_color="green")
        else:
            self.status_label.configure(text="🔴 No API Key", text_color="red")
    
    def center_window(self):
        """Center the window on screen"""
        self.window.update_idletasks()
        width = 650
        height = 550
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def toggle_window(self):
        """Toggle window visibility"""
        if self.is_visible:
            self.hide_window()
        else:
            self.show_window()
    
    def show_window(self):
        """Show the overlay window"""
        try:
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
            self.window.attributes('-topmost', True)
            self.query_entry.focus()
            self.is_visible = True
            print("Window shown")
        except Exception as e:
            print(f"Error showing window: {e}")
    
    def hide_window(self):
        """Hide the overlay window"""
        try:
            self.window.withdraw()
            self.is_visible = False
            print("Window hidden")
        except Exception as e:
            print(f"Error hiding window: {e}")
    
    def send_query(self, event=None):
        """Send query to Gemini"""
        query = self.query_entry.get().strip()
        if not query:
            return
        
        if not self.model:
            self.show_api_key_dialog()
            return
        
        # Disable send button and clear input
        self.send_btn.configure(state="disabled", text="Sending...")
        self.query_entry.delete(0, 'end')
        
        # Add user message to history
        timestamp = datetime.now().strftime("%H:%M")
        user_entry = {
            "type": "user",
            "content": query,
            "timestamp": timestamp
        }
        self.chat_history.append(user_entry)
        
        # Show "thinking" message
        thinking_entry = {
            "type": "assistant",
            "content": "🤔 Thinking...",
            "timestamp": timestamp
        }
        self.chat_history.append(thinking_entry)
        self.refresh_chat_display()
        
        # Send query in thread to avoid blocking UI
        modified_query = self.apply_mode_to_query(query)
        thread = threading.Thread(target=self.get_gemini_response, args=(modified_query, query))
        thread.daemon = True
        thread.start()
    
    def get_gemini_response(self, modified_query, original_query):
        """Get response from Gemini API"""
        try:
            response = self.model.generate_content(modified_query)
            
            # Remove "thinking" message
            if self.chat_history and self.chat_history[-1]["content"] == "🤔 Thinking...":
                self.chat_history.pop()
            
            # Add AI response (show the mode in the timestamp)
            timestamp = datetime.now().strftime("%H:%M")
            modes = self.get_mode_prompts()
            mode_display = modes[self.current_mode]["name"]
            
            ai_entry = {
                "type": "assistant",
                "content": response.text,
                "timestamp": f"{timestamp} • {mode_display}",
                "mode": self.current_mode
            }
            self.chat_history.append(ai_entry)
            
        except Exception as e:
            print(f"Error getting Gemini response: {e}")
            # Remove "thinking" message
            if self.chat_history and self.chat_history[-1]["content"] == "🤔 Thinking...":
                self.chat_history.pop()
            
            # Add error message
            timestamp = datetime.now().strftime("%H:%M")
            error_entry = {
                "type": "assistant",
                "content": f"❌ Error: {str(e)}\n\nPlease check your API key or try again.",
                "timestamp": timestamp
            }
            self.chat_history.append(error_entry)
        
        # Update display and save history
        self.window.after(0, self.refresh_chat_display_and_enable_send)
        self.save_history()
    
    def refresh_chat_display_and_enable_send(self):
        """Refresh display and re-enable send button"""
        self.refresh_chat_display()
        self.send_btn.configure(state="normal", text="Send")
    
    def refresh_chat_display(self):
        """Refresh the chat display"""
        self.chat_display.delete("1.0", "end")
        
        if not self.chat_history:
            modes = self.get_mode_prompts()
            current_mode_name = modes[self.current_mode]["name"]
            
            # Get current model display name
            current_model_name = "Unknown"
            for name, model_id in self.available_models.items():
                if model_id == self.current_model:
                    current_model_name = name
                    break
                    
            pinned_info = f"\n📌 Pinned Context: {len(self.pinned_context)} items" if self.pinned_context else ""
            
            # *** UPDATED: Welcome Text ***
            welcome_text = f"""👋 Welcome to Gemini Everywhere!

🎭 Current Mode: {current_mode_name}
🤖 Current Model: {current_model_name}{pinned_info}

🚀 Quick Actions:
Click the "Commands" button below for a list of quick actions like summarizing, translating, and fixing code.

💡 Features:
• Use the "Commands" button for quick access to actions
• Change modes and models using the dropdowns above
• Pin important context with the "Pin Context" button
• Copy the last response with the "Copy Last" button
• Use Ctrl+Space from anywhere to toggle the window
"""
            self.chat_display.insert("end", welcome_text)
        else:
            for entry in self.chat_history:
                timestamp = entry.get("timestamp", "")
                content = entry["content"]
                
                if entry["type"] == "user":
                    self.chat_display.insert("end", f"[{timestamp}] You:\n{content}\n\n")
                else:
                    self.chat_display.insert("end", f"[{timestamp}] Gemini:\n{content}\n\n")
        
        # Scroll to bottom
        self.chat_display.see("end")
    
    def clear_history(self):
        """Clear chat history"""
        self.chat_history = []
        self.refresh_chat_display()
        self.save_history()
        print("Chat history cleared")
    
    def show_help(self):
        """Show help dialog"""
        help_window = ctk.CTkToplevel(self.window)
        help_window.title("Help - Gemini Everywhere")
        help_window.geometry("500x400")
        help_window.attributes('-topmost', True)
        help_window.transient(self.window)
        
        help_text = """🤖 Gemini Everywhere - Help

🔥 HOTKEY:
• Ctrl+Space - Toggle window from anywhere

⌨️ SHORTCUTS:
• Enter - Send message
• Ctrl+Enter - New line in message
• Esc - Hide window

🚀 QUICK COMMANDS:
• Use the "Commands" button for easy access to common tasks like summarizing, translating, and code analysis.

🎭 CONVERSATION MODES:
• 🤖 Normal - Standard helpful responses
• 😎 Informal - Casual, friendly chat style
• 👔 Professional - Formal business tone
• 🎨 Creative - Imaginative and artistic responses
• 📚 Teacher - Educational, step-by-step explanations
• 💻 Coder - Programming focused with code examples
• ⚡ Concise - Brief, to-the-point answers
• 🔍 Analyzer - Systematic problem analysis
• 💡 Brainstormer - Creative idea generation

🔧 SETUP:
1. Click "API Key"
2. Get a free API key from: https://makersuite.google.com/app/apikey
3. Paste the key and click Save

❓ TROUBLESHOOTING:
• Red status? Configure your API key.
• Hotkey not working? Try running as administrator.

Made with ❤️ for quick AI assistance!"""
        
        help_display = ctk.CTkTextbox(help_window, wrap="word")
        help_display.pack(fill="both", expand=True, padx=20, pady=20)
        help_display.insert("1.0", help_text)
        help_display.configure(state="disabled")
        
        close_btn = ctk.CTkButton(help_window, text="Close", command=help_window.destroy)
        close_btn.pack(pady=10)
    
    def show_api_key_dialog(self):
        """Show API key configuration dialog"""
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("Configure Gemini API Key")
        dialog.geometry("500x300")
        dialog.attributes('-topmost', True)
        dialog.transient(self.window)
        dialog.grab_set()
        
        # Instructions
        instructions = ctk.CTkLabel(
            dialog, 
            text="""🔑 Gemini API Key Required

1. Visit: https://makersuite.google.com/app/apikey
2. Click "Create API Key" 
3. Copy your key and paste it below
4. Click Save

Your key will be stored securely on your device.""",
            wraplength=450,
            justify="left"
        )
        instructions.pack(pady=20, padx=20)
        
        # API key entry
        key_frame = ctk.CTkFrame(dialog)
        key_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(key_frame, text="API Key:").pack(anchor="w", padx=10, pady=(10, 5))
        
        api_entry = ctk.CTkEntry(key_frame, width=400, show="*", placeholder_text="Paste your Gemini API key here...")
        api_entry.pack(padx=10, pady=(0, 10), fill="x")
        
        # Current API key indicator
        if self.api_key:
            current_label = ctk.CTkLabel(dialog, text="✅ API key is currently configured", text_color="green")
            current_label.pack(pady=5)
            # Don't show the actual key for security
        
        # Buttons
        button_frame = ctk.CTkFrame(dialog)
        button_frame.pack(pady=20)
        
        def save_and_test_key():
            key = api_entry.get().strip()
            if not key:
                messagebox.showerror("Error", "Please enter an API key!")
                return
                
            # Show progress
            save_btn.configure(text="Testing...", state="disabled")
            dialog.update()
            
            try:
                # Test the API key with a simple request
                genai.configure(api_key=key)
                test_model = genai.GenerativeModel('gemini-1.5-pro')
                # Try a minimal generation to verify the key works
                test_response = test_model.generate_content("Hi")
                
                # If we get here, the key works - now save it
                if self.save_api_key(key):
                    self.api_key = key
                    self.model = test_model
                    self.update_status()
                    messagebox.showinfo("Success", "✅ API key saved and verified successfully!")
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "❌ API key works but failed to save to file!")
                    save_btn.configure(text="Save & Test", state="normal")
            except Exception as e:
                error_msg = str(e)
                if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
                    messagebox.showerror("Invalid API Key", "❌ The API key you entered is invalid.\n\nPlease check:\n• Key is copied correctly\n• No extra spaces\n• Key is from Google AI Studio")
                else:
                    messagebox.showerror("Connection Error", f"❌ Could not verify API key:\n{error_msg}\n\nThe key will be saved anyway - try using it.")
                    # Save anyway in case it's just a network issue
                    if self.save_api_key(key):
                        self.api_key = key
                        genai.configure(api_key=key)
                        self.model = genai.GenerativeModel('gemini-1.5-pro')
                        self.update_status()
                        dialog.destroy()
                save_btn.configure(text="Save & Test", state="normal")
        
        def save_without_test():
            key = api_entry.get().strip()
            if not key:
                messagebox.showerror("Error", "Please enter an API key!")
                return
            
            if self.save_api_key(key):
                self.api_key = key
                genai.configure(api_key=key)
                self.model = genai.GenerativeModel('gemini-1.5-pro')
                self.update_status()
                messagebox.showinfo("Saved", "✅ API key saved successfully!\n(Not tested - will verify on first use)")
                dialog.destroy()
            else:
                messagebox.showerror("Error", "❌ Failed to save API key to file!")
        
        save_btn = ctk.CTkButton(button_frame, text="Save & Test", command=save_and_test_key)
        save_btn.pack(side="left", padx=5)
        
        save_only_btn = ctk.CTkButton(button_frame, text="Save Only", command=save_without_test)
        save_only_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(button_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side="left", padx=5)
        
        api_entry.focus()
        api_entry.bind("<Return>", lambda e: save_and_test_key())
        
        # Bind Escape to close
        dialog.bind("<Escape>", lambda e: dialog.destroy())
    
    def on_closing(self):
        """Handle window closing"""
        self.hide_window()
    
    def run(self):
        """Run the application"""
        print("\n🚀 Gemini Everywhere Starting...")
        print("📝 Press Ctrl+Space anywhere to toggle the overlay!")
        print("⚙️  Configure your API key when prompted.")
        print("❌ Close the window or press Ctrl+C to quit")
        print("-" * 50)
        
        try:
            # Show window initially for first-time setup
            if not self.api_key:
                print("👋 Opening window for initial setup...")
                self.window.after(1000, self.show_window)  # Show after 1 second
            
            # Run the GUI event loop
            self.window.mainloop()
            
        except KeyboardInterrupt:
            print("\n👋 Shutting down Gemini Everywhere...")
        except Exception as e:
            print(f"Error running application: {e}")
        finally:
            self.running = False

def main():
    try:
        app = GeminiEverywhere()
        app.run()
    except Exception as e:
        print(f"Failed to start application: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
