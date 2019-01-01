
from PyQt5.QtWebEngineCore import (
    QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo,
)
from PyQt5.QtWebEngineWidgets import (
    QWebEngineView, QWebEngineProfile, QWebEnginePage, QWebEngineSettings,
)


class Interceptor(QWebEngineUrlRequestInterceptor):
    accepted_types = (
        QWebEngineUrlRequestInfo.ResourceTypeStylesheet,
        QWebEngineUrlRequestInfo.ResourceTypeImage,
        QWebEngineUrlRequestInfo.ResourceTypeMainFrame,
    )

    def interceptRequest(self, req):
        if req.resourceType() not in self.accepted_types:
            req.block(True)
            return

        url = req.requestUrl().toString()
        if not url.startswith('data:'):
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

