
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PyQt5.QtWebEngineWidgets import (
    QWebEngineView, QWebEngineProfile, QWebEnginePage, QWebEngineSettings,
)


class Interceptor(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, req):
        url = req.requestUrl().toString()
        if not url.startswith('data:'):
            print(bytes(req.requestMethod()).decode('ascii'), req.requestUrl().toString(), req.navigationType(), req.resourceType())
            req.block(True)


class WebView(QWebEngineView):
    def __init__(self, *args, **kwargs):
        super(WebView, self).__init__(*args, **kwargs)

        self.interceptor = Interceptor(self)

        self.profile = QWebEngineProfile(self)
        self.profile.setRequestInterceptor(self.interceptor)

        self.setPage(QWebEnginePage(self.profile, self))

        self._restrict()

    def _restrict(self):
        self.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, False)

