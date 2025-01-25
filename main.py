import customtkinter
from pynput import keyboard
import asyncio
import google.generativeai as genai
import os
import threading
import time
import traceback

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("Please set the GOOGLE_API_KEY environment variable")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')


class GeminiOverlay:
    def __init__(self):
        self.root = customtkinter.CTk()
        self.root.title("Gemini Overlay")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "black")
        self.root.geometry("800x100+200+200")
        self.root.configure(fg_color="black")

        self.is_shown = False
        self.fade_step = 0.05
        self.animation_duration = 0.25
        self.target_height = 100
        self.target_y = 200
        self.response_frame_y = 0
        self.response_frame_height = 0
        self.is_loading = False

        self.setup_ui()
        self.setup_keyboard_listener()

    def setup_ui(self):
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
        self.input_box.place(relx=0.5, rely=0.2, anchor="center")
        self.input_box.bind("<Return>", self.query_gemini)
        self.input_box.bind("<Escape>", self.hide_window)

        self.response_frame = customtkinter.CTkFrame(
            self.root,
            fg_color="gray15",
            corner_radius=0,
            width=700,
            height=0
        )
        self.response_frame.place(relx=0.5, rely=0.5, anchor="n")

        self.response_label = customtkinter.CTkLabel(
            self.response_frame,
            text="",
            wraplength=680,
            justify="left",
            font=("Arial", 12),
            text_color="gray90"
        )
        self.response_label.place(relx=0.5, rely=0.1, anchor="n")

        self.root.withdraw()

    def setup_keyboard_listener(self):
        self._alt_pressed = False
        self._space_pressed = False
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.keyboard_listener.start()

    @property
    def hotkey_pressed(self):
        return self._alt_pressed and self._space_pressed

    def on_press(self, key):
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_gr):
            self._alt_pressed = True
        elif key == keyboard.Key.space:
            self._space_pressed = True
            if self.hotkey_pressed:
                return False
        return True

    def on_release(self, key):
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_gr):
            self._alt_pressed = False
        elif key == keyboard.Key.space:
            self._space_pressed = False

    def show_window(self):
        if not self.is_shown:
            self.root.deiconify()
            self.root.attributes("-alpha", 0.0)
            self.is_shown = True
            threading.Thread(target=self._animate_window, args=(1.0,), daemon=True).start()
            self.root.after(100, self._set_focus)  # Delay focus to ensure window is ready

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
        self.input_box.delete(0, "end")
        self.response_label.configure(text="")
        self.target_height = 100
        self.target_y = 200
        self.response_frame_height = 0
        self.response_frame_y = 0
        self.response_frame.configure(height=0)
        self.root.geometry(f"800x{self.target_height}+200+{self.target_y}")

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
            self.response_label.configure(text="Loading...")
            threading.Thread(
                target=self._fetch_gemini_response,
                args=(query,),
                daemon=True
            ).start()

    async def _get_gemini_response(self, query):
        try:
            response = await model.generate_content_async(query)
            await response.resolve()
            return response.text if response and response.text else "No response"
        except Exception as e:
            return f"Error: {str(e)}"

    def _fetch_gemini_response(self, query):
        async def async_query():
            try:
                response = model.generate_content(query)
                return response.text if response and response.text else "No response"
            except Exception as e:
                return f"Error: {str(e)}\n{traceback.format_exc()}"

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(async_query())
            loop.close()
            self._update_response_panel(response)
        except Exception as e:
            self._update_response_panel(f"Error: {str(e)}\n{traceback.format_exc()}")
        finally:
            self.is_loading = False
            self.reset_input()
            self.input_box.focus_set()

    def _update_response_panel(self, response_text):
        if not response_text or response_text.startswith("Error:"):
            self.response_label.configure(text=response_text)
            return

        self.response_label.configure(text=response_text)
        self.root.update_idletasks()
        required_height = self.response_label.winfo_reqheight() + 20
        self.response_frame_height = required_height
        self.response_frame_y = (
                self.input_box.winfo_y() +
                self.input_box.winfo_height() +
                10
        )
        self._animate_response_panel(required_height)

    def _animate_response_panel(self, required_height):
        start_time = time.time()
        start_height = 0
        start_y = self.response_frame.winfo_y()

        def animate_step():
            nonlocal start_time, start_height, start_y
            elapsed_time = time.time() - start_time
            progress = elapsed_time / self.animation_duration

            self.response_frame_height = int(
                start_height + (required_height - start_height) * progress
            )
            self.response_frame.configure(height=self.response_frame_height)

            y = int(start_y + (self.response_frame_y - start_y) * progress)
            self.response_frame.place(relx=0.5, rely=0, y=y, anchor="n")

            if time.time() - start_time < self.animation_duration:
                self.root.after(10, animate_step)
            else:
                self.response_frame_height = required_height
                self.response_frame.configure(height=self.response_frame_height)
                self.response_frame.place(
                    relx=0.5,
                    rely=0,
                    y=self.response_frame_y,
                    anchor="n"
                )

        animate_step()


def on_alt_space():
    if not overlay.hotkey_pressed:
        return
    if overlay.is_shown:
        overlay.hide_window()
    else:
        overlay.show_window()


if __name__ == "__main__":
    overlay = GeminiOverlay()
    with keyboard.GlobalHotKeys({"<alt>+<space>": on_alt_space}) as h:
        overlay.root.mainloop()