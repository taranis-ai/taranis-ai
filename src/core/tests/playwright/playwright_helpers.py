import time

class PlaywrightHelpers:

    def smooth_scroll(self, locator):
        locator.evaluate("""
            element => {
                element.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center',
                    inline: 'nearest'
                });
            }
        """)

    def highlight_element(self, locator, scroll: bool = True, transition: bool = True):
        if self.ci_run:
            return locator
        style_content = """
        .highlight-element { background-color: yellow !important; outline: 4px solid red !important; }
        """

        wait_duration = self.wait_duration if transition else 1

        if scroll:
            self.smooth_scroll(locator)

        style_tag = locator.page.add_style_tag(content=style_content)
        locator.evaluate("element => element.classList.add('highlight-element')")
        self.short_sleep(wait_duration)
        locator.evaluate("element => element.classList.remove('highlight-element')")
        locator.page.evaluate("style => style.remove()", style_tag)
        return locator

    def add_keystroke_overlay(self, page):
        if self.ci_run:
            return
        style_content = """
            .keystroke-overlay {
                position: fixed;
                bottom: 10px;
                right: 10px;
                padding: 10px 20px;
                background-color: grey;
                color: white;
                font-family: Arial, sans-serif;
                font-size: 48px;
                border: 3px solid red;
                border-radius: 5px;
                z-index: 10000;
                display: none;
            }
            """
        page.add_style_tag(content=style_content)

        # Inject the overlay div
        page.evaluate("""
            const overlay = document.createElement('div');
            overlay.className = 'keystroke-overlay';
            document.body.appendChild(overlay);
            """)

        # Add event listener to capture keystrokes and display them
        page.evaluate("""
            document.addEventListener('keydown', (event) => {
                let keys = [];
                if (event.ctrlKey) keys.push('Control');
                if (event.shiftKey) keys.push('Shift');
                if (event.altKey) keys.push('Alt');
                if (event.metaKey) keys.push('Meta');  // For Mac Command key
                if (event.key && !['Control', 'Shift', 'Alt', 'Meta'].includes(event.key)) {
                    keys.push(event.key === ' ' ? 'Space' : event.key);
                }
                if (event.key === 'Escape') {
                    keys = ['Escape'];
                }
                const overlay = document.querySelector('.keystroke-overlay');
                overlay.textContent = keys.join('+');
                overlay.style.display = 'block';

                setTimeout(() => {
                    overlay.style.display = 'none';
                }, 1000);  // Display for 1 seconds
            });
            """)

    def short_sleep(self, duration=0.2):
        if self.ci_run:
            return
        time.sleep(duration)
