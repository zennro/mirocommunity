"""Google specific login.

"""
from localtv.tests.selenium.pages import Page


class Google(Page):
    """Google login pages.

    """

    _GOOGLE_PAGE = "div.google-header-bar"
    _APPROVE = "button#submit_approve_access:enabled"
    _EMAIL = "input#Email"
    _PASSWORD = "input#Passwd"
    _SUBMIT = "input#signIn.g-button"

    def google_login(self, user, passw, **kwargs):
        """Enter info into google login form.

        """
        self.wait_for_element_present(self._GOOGLE_PAGE, wait_time=10)
        if self.is_element_present(self._EMAIL):
            self.type_by_css(self._EMAIL, user)
            self.type_by_css(self._PASSWORD, passw)
            self.click_by_css(self._SUBMIT)
        try:
            self.wait_for_element_present(self._APPROVE, wait_time=15)
        except:
            pass   # this doesn't always display.
        if self.is_element_present(self._APPROVE):
            self.click_by_css(self._APPROVE)
