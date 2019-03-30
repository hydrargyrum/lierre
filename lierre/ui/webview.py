
import logging

from PyQt5.QtCore import QSizeF, pyqtSlot as Slot, QBuffer, QByteArray
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWebEngineCore import (
    QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo,
    QWebEngineUrlSchemeHandler,
)
from PyQt5.QtWebEngineWidgets import (
    QWebEngineView, QWebEngineProfile, QWebEnginePage, QWebEngineSettings,
)


LOGGER = logging.getLogger(__name__)


class CidSchemeHandler(QWebEngineUrlSchemeHandler):
    def __init__(self, *args, **kwargs):
        super(CidSchemeHandler, self).__init__(*args, **kwargs)
        self.pymessage = None
        self.parts = {}

    def setMessage(self, pymessage):
        self.pymessage = pymessage

        self.parts = {}
        for part in self.pymessage.iter_attachments():
            cid = part.get('Content-ID')
            if not cid:
                continue

            self.parts[cid[1:-1]] = part

    def requestStarted(self, req):
        if req.requestMethod() != b'GET':
            return req.fail(req.RequestFailed)

        path = req.requestUrl().path()
        try:
            part = self.parts[path]
        except KeyError:
            return req.fail(req.UrlNotFound)

        qbuf = QBuffer(parent=req)
        # XXX decode=True: decodes message ASCII to bytes
        qbuf.setData(QByteArray(part.get_payload(decode=True)))
        req.reply(part.get_content_type().encode('ascii'), qbuf)


class Interceptor(QWebEngineUrlRequestInterceptor):
    accepted_types = (
        QWebEngineUrlRequestInfo.ResourceTypeStylesheet,
        QWebEngineUrlRequestInfo.ResourceTypeImage,
        QWebEngineUrlRequestInfo.ResourceTypeMainFrame,
    )

    def interceptRequest(self, req):
        url = req.requestUrl().toString()
        method = bytes(req.requestMethod()).decode('ascii')

        if method == 'GET' and req.navigationType() == QWebEngineUrlRequestInfo.NavigationTypeLink:
            # warning: clicks must be accepted else acceptNavigationRequest() won't be called
            # and worse: the page will be blanked due to what looks like a qt bug
            LOGGER.debug('accepted click request %s %s (navigation: %s, resource: %s)', method, url, req.navigationType(), req.resourceType())
            return

        if method != 'GET' or req.resourceType() not in self.accepted_types:
            req.block(True)
            LOGGER.debug('blocked request %s %s (navigation: %s, resource: %s)', method, url, req.navigationType(), req.resourceType())
            return

        if not url.startswith('data:') and not url.startswith('cid:'):
            req.block(True)
            LOGGER.debug('blocked request %s %s (navigation: %s, resource: %s)', method, url, req.navigationType(), req.resourceType())
            return


class WebEnginePage(QWebEnginePage):
    accepted = (
        QWebEnginePage.NavigationTypeBackForward,
        QWebEnginePage.NavigationTypeTyped,
    )

    def acceptNavigationRequest(self, qurl, nav_type, is_main_frame):
        if nav_type in self.accepted:
            return True
        if nav_type == QWebEnginePage.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(qurl)
        return False


class WebView(QWebEngineView):
    def __init__(self, *args, **kwargs):
        super(WebView, self).__init__(*args, **kwargs)

        self.interceptor = Interceptor(self)
        self.cid_handler = CidSchemeHandler(self)

        self.profile = QWebEngineProfile(self)
        self.profile.setRequestInterceptor(self.interceptor)
        self.profile.installUrlSchemeHandler(b'cid', self.cid_handler)

        self.setPage(WebEnginePage(self.profile, self))
        self.page().contentsSizeChanged.connect(self._pageSizeChanged)

        self._restrict()

        # warning: the signal is emitted with an empty string if the link isn't hovered anymore
        self.page().linkHovered.connect(self.window().statusBar().showMessage)

    def _restrict(self):
        self.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, False)

    @Slot(QSizeF)
    def _pageSizeChanged(self, size):
        self.updateGeometry()

    def minimumSizeHint(self):
        return self.page().contentsSize().toSize()

    def setMessage(self, pymessage):
        self.cid_handler.setMessage(pymessage)
