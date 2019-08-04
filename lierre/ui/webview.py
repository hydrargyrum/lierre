# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

import logging

from PyQt5.QtCore import (
    QSizeF, pyqtSlot as Slot, QBuffer, QByteArray, QVariant, QTimer,
)
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QTextBrowser
from PyQt5.QtWebEngineCore import (
    QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo,
    QWebEngineUrlSchemeHandler,
)
from PyQt5.QtWebEngineWidgets import (
    QWebEngineView, QWebEngineProfile, QWebEnginePage, QWebEngineSettings,
)


LOGGER = logging.getLogger(__name__)
ENGINE_LOGGER = LOGGER.getChild('webengine')
TEXT_LOGGER = LOGGER.getChild('textbrowser')


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
            ENGINE_LOGGER.debug('prevented non-GET to cid: resource')
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
            ENGINE_LOGGER.debug('accepted click request %s %s (navigation: %s, resource: %s)', method, url, req.navigationType(), req.resourceType())
            return

        if method != 'GET' or req.resourceType() not in self.accepted_types:
            req.block(True)
            ENGINE_LOGGER.debug('blocked request %s %s (navigation: %s, resource: %s)', method, url, req.navigationType(), req.resourceType())
            return

        if not url.startswith('data:') and not url.startswith('cid:'):
            req.block(True)
            ENGINE_LOGGER.debug('blocked request %s %s (navigation: %s, resource: %s)', method, url, req.navigationType(), req.resourceType())
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


class WebEngineView(QWebEngineView):
    def __init__(self, *args, **kwargs):
        super(WebEngineView, self).__init__(*args, **kwargs)

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


class TextBrowserView(QTextBrowser):
    def __init__(self, *args, **kwargs):
        super(TextBrowserView, self).__init__(*args, **kwargs)
        self.setOpenExternalLinks(True)

        self.pymessage = None

        self._resizeTimer = QTimer(parent=self)
        self._resizeTimer.setSingleShot(True)
        self._resizeTimer.setInterval(0)
        self._resizeTimer.timeout.connect(self.updateSize)

    def setMessage(self, pymessage):
        self.pymessage = pymessage

        self.parts = {}
        for part in self.pymessage.walk():
            cid = part.get('Content-ID')
            if not cid:
                continue

            self.parts[cid[1:-1]] = part

    def loadResource(self, type, qurl):
        url = bytes(qurl.toEncoded()).decode('ascii')
        if qurl.scheme() != 'cid':
            TEXT_LOGGER.debug('preventing %r to be loaded', url)
            return QVariant()

        TEXT_LOGGER.debug('loading %r from parts', url)
        path = qurl.path()
        try:
            part = self.parts[path]
        except KeyError:
            TEXT_LOGGER.debug('could not find part %r', path)
            return QVariant()

        self._resizeTimer.start()
        # XXX decode=True: decodes message ASCII to bytes
        return QVariant(QByteArray(part.get_payload(decode=True)))

    @Slot(str)
    def setHtml(self, s):
        self._resizeTimer.start()
        return super(TextBrowserView, self).setHtml(s)

    def sizeHint(self):
        sz = self.document().size().toSize()
        sz.setHeight(20 + sz.height())
        return sz

    @Slot()
    def updateSize(self):
        self.updateGeometry()


WebView = TextBrowserView
