import customtkinter
from pynput import keyboard
import asyncio
import google.generativeai as genai
import os
import threading
import time
import traceback
import pyperclip

# Initialize Google API configuration
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("Please set the GOOGLE_API_KEY environment variable")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')


class GeminiOverlay:
    def __init__(self):
        # Initialize main window settings
        self.root = customtkinter.CTk()
        self.root.title("Gemini Overlay")
        self.root.overrideredirect(True)  # Remove window decorations
        self.root.attributes("-topmost", True)  # Keep window on top
        self.root.attributes("-transparentcolor", "black")
        self.root.geometry("800x500+200+200")  # Set a static height
        self.root.configure(fg_color="black")

        # Initialize conversation history for API context
        self.api_conversation_history = []  # List to store conversation entries

        # Configuration settings
        self.is_shown = False
        self.fade_step = 0.05
        self.animation_duration = 0.25
        self.max_response_height = 400  # Maximum height for response panel
        self.fixed_response_height = 200  # Fixed response height
        self.input_box_x = 400  # Location of input box, center of screen (800 px width / 2)
        self.input_box_y = 30  # Input box location
        self.is_loading = False  # Initialize the is_loading attribute
        self.button_width = 40  # Common width for buttons
        self.button_height = 30
        self.button_corner_radius = 8  # Common corner radius for buttons
        self.button_y_position = 450  # Set the vertical position

        # Initialize UI components and keyboard listener
        self.setup_ui()
        self.setup_keyboard_listener()

    def setup_ui(self):
        # Create and configure the input box with fixed position
        self.input_box = customtkinter.CTkEntry(
            self.root,
            placeholder_text="Ask Gemini...",
            fg_color="gray20",
            text_color="white",
            border_color="gray30",
            width=700,
            height=30,
            font=("Arial", 14),
            justify="center"
        )
        # Place input box at a fixed distance from top instead of using relative positioning
        self.input_box.place(x=self.input_box_x, y=self.input_box_y, anchor="center")
        self.input_box.bind("<Return>", self.query_gemini)
        self.input_box.bind("<Escape>", self.hide_window)

        # Create main response frame
        self.response_frame = customtkinter.CTkFrame(
            self.root,
            fg_color="gray15",
            corner_radius=10,  # Add corner radius here
            width=640,
            height=self.fixed_response_height
        )
        response_frame_y = self.input_box_y + 15  # Set the vertical position
        self.response_frame.place(x=self.input_box_x, y=response_frame_y, anchor="n")  # Fix y and keep it below input box

        # Create scrollable frame for response content
        self.scrollable_frame = customtkinter.CTkScrollableFrame(
            self.response_frame,
            width=645,
            height=self.fixed_response_height - 20,
            fg_color="gray15",
            corner_radius=20,  # Add corner radius here
            scrollbar_button_color="gray30",
            scrollbar_button_hover_color="gray40"
        )
        self.scrollable_frame.pack(expand=True, fill="both", padx=10, pady=10)

        # Create text widget for history display inside scrollable frame
        self.response_text = customtkinter.CTkTextbox(
            self.scrollable_frame,
            width=640,
            wrap="word",
            font=("Arial", 12),
            text_color="gray90",
            fg_color="transparent",
            border_width=0,
            activate_scrollbars=True
        )
        self.response_text.pack(expand=True, fill="both", padx=5, pady=5)
        self.response_text.configure(state="disabled")  # Make text read-only by default

        # Create copy label with text-based icon
        self.copy_label = customtkinter.CTkLabel(
            self.scrollable_frame,
            text="copy", #Using numbers to draw an icon
            font=("Arial", 14),  # Set the font size and type
            text_color="gray70",  # Set the text color
            cursor="hand2", #Set cursor to hand pointer on hover
            fg_color="gray20", # Set background color
            corner_radius=5,
        )
        self.copy_label.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)
        self.copy_label.bind("<Button-1>", self.copy_to_clipboard)  # Bind click event

        # Initially hide the window
        self.root.withdraw()

    def setup_keyboard_listener(self):
        # Initialize keyboard tracking variables
        self._ctrl_pressed = False
        self._space_pressed = False
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.keyboard_listener.start()

    @property
    def hotkey_pressed(self):
        return self._ctrl_pressed and self._space_pressed

    def on_press(self, key):
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self._ctrl_pressed = True
        elif key == keyboard.Key.space:
            self._space_pressed = True
            if self.hotkey_pressed:
                return False
        return True

    def on_release(self, key):
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self._ctrl_pressed = False
        elif key == keyboard.Key.space:
            self._space_pressed = False

    def show_window(self):
        if not self.is_shown:
            self.root.deiconify()
            self.root.attributes("-alpha", 0.0)
            self.is_shown = True
            threading.Thread(target=self._animate_window, args=(1.0,), daemon=True).start()
            self.root.after(100, self._set_focus)

    def _set_focus(self):
        self.root.focus_force()
        self.input_box.focus_set()
        self.reset_input()

    def hide_window(self, event=None):
        if self.is_shown and not self.is_loading:
            threading.Thread(target=self._animate_window, args=(0.0,), daemon=True).start()
            self.reset_ui()
            self.is_shown = False

    def reset_ui(self):
        # Reset all UI elements to their initial state
        self.input_box.delete(0, "end")
        self.response_text.configure(state="normal")
        self.response_text.delete("1.0", "end")
        self.response_text.configure(state="disabled")
        self.root.geometry("700x500+200+200")  # Reset to the original static height
        # Clear conversation history for API when window is closed
        self.api_conversation_history = []

    def reset_input(self):
        self.input_box.configure(
            state="normal",
            placeholder_text="Ask Gemini...",
            text_color="white"
        )
        self.input_box.delete(0, "end")

    def _animate_window(self, target_alpha):
        current_alpha = self.root.attributes("-alpha")
        while abs(current_alpha - target_alpha) > 0.01:
            if current_alpha < target_alpha:
                current_alpha += self.fade_step
            else:
                current_alpha -= self.fade_step
            self.root.attributes("-alpha", current_alpha)
            time.sleep(0.01)
        if target_alpha == 0.0:
            self.root.withdraw()

    def query_gemini(self, event=None):
        query = self.input_box.get().strip()
        if query and not self.is_loading:
            self.is_loading = True
            self.input_box.configure(
                state="disabled",
                placeholder_text="Loading...",
                text_color="gray70"
            )
            # Update loading state in text widget
            self.response_text.configure(state="normal")
            self.response_text.delete("1.0", "end")
            self.response_text.insert("end", "Loading...")
            self.response_text.configure(state="disabled")

            # Start response fetch in background
            threading.Thread(
                target=self._fetch_gemini_response,
                args=(query,),
                daemon=True
            ).start()

    async def _get_gemini_response(self, query):
        try:
            # Format the prompt with history
            prompt_with_history = self._build_prompt_with_history(query)
            response = await model.generate_content_async(prompt_with_history)
            await response.resolve()
            return response.text if response and response.text else "No response"
        except Exception as e:
            return f"Error: {str(e)}"

    def _build_prompt_with_history(self, current_query):
        """Builds a prompt that includes the current query and previous
        turns of the conversation with Gemini without displaying on screen
        """
        prompt = ""
        for entry in self.api_conversation_history:
            prompt += f"User: {entry['query']}\nGemini: {entry['response']}\n"
        prompt += f"User: {current_query}\nGemini: "
        return prompt


    def _fetch_gemini_response(self, query):
        async def async_query():
            try:
                # Format the prompt with history
                prompt_with_history = self._build_prompt_with_history(query)
                response = model.generate_content(prompt_with_history)
                return response.text if response and response.text else "No response"
            except Exception as e:
                return f"Error: {str(e)}\n{traceback.format_exc()}"

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(async_query())
            loop.close()
            self._update_response_panel(query, response)
        except Exception as e:
            self._update_response_panel(query, f"Error: {str(e)}\n{traceback.format_exc()}")
        finally:
            self.is_loading = False
            self.reset_input()
            self.input_box.focus_set()

    def _update_response_panel(self, query, response_text):
        # Add the new conversation entry to history for the API
        self.api_conversation_history.append({
            'query': query,
            'response': response_text
        })

        # Update the text widget to show only the response
        self.response_text.configure(state="normal")
        self.response_text.delete("1.0", "end")

        # Display only the response text, without any labels
        self.response_text.insert("end", response_text)

        # Make text read-only again
        self.response_text.configure(state="disabled")

    def copy_to_clipboard(self, event=None):
        self.response_text.configure(state="normal")
        text_to_copy = self.response_text.get("1.0", "end-1c")
        pyperclip.copy(text_to_copy)
        self.response_text.configure(state="disabled")


def on_ctrl_space():
    if not overlay.hotkey_pressed:
        return
    if overlay.is_shown:
        overlay.hide_window()
    else:
        overlay.show_window()


if __name__ == "__main__":
    overlay = GeminiOverlay()
    with keyboard.GlobalHotKeys({"<ctrl>+<space>": on_ctrl_space}) as h:
        overlay.root.mainloop()