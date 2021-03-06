"""The /listing pages.

"""
from localtv.tests.selenium.pages import Page
import time


class ListingPage(Page):
    """Define all the elements common to the listing pages.

    """
    _NEW_PAGE = 'listing/new/'
    _POPULAR_PAGE = 'listing/popular/'
    _FEATURED_PAGE = 'listing/featured/'
    _CATEGORY_PAGE = 'category/%s'
    _THUMBNAIL = '.tiles-item img'
    _TITLE = '.grid-item-header h1'
    _FEED_PAGE = 'feeds/%s'
    _HOVER = '.popover-trigger'
    _BYLINE = '.byline a'
    _PAGE_NAME = 'header.page-header h1'
    _PAGE_RSS = 'header.page-header a.rss'

    def page_name(self):
        """Return the name of the page from the heading.

        """
        return self.get_text_by_css(self._PAGE_NAME)

    def page_rss(self):
        """Return the page rss feed link.

        """
        return self.get_element_attribute(self._PAGE_RSS, 'href')

    def open_listing_page(self, listing):
        """Open the given listing page.

       """
        valid_pages = ('new', 'popular', 'featured')
        if listing not in valid_pages:
            assert False, "page must be either %s pages" % str(valid_pages)
        listing_pg_url = getattr(self, "_".join(['', listing.upper(), 'PAGE']))
        self.open_page(listing_pg_url)

    def open_listing_rss_page(self, listing):
        """Open the /feed/ page of the giving listing page.

        """
        valid_pages = ('new', 'popular', 'featured')
        if listing not in valid_pages:
            assert False, "page must be either %s pages" % str(valid_pages)
        self.open_page(self._FEED_PAGE % listing)

    def open_category_page(self, category):
        """Open a category page via the url.

        """
        category_pg_url = self._CATEGORY_PAGE % category
        self.open_page(category_pg_url)

    def has_thumbnails(self):
        """Return True if the displayed page has thumbnails.

        """
        time.sleep(2)
        if self.is_element_present(self._THUMBNAIL):
            return True

    def default_thumbnail_percent(self):
        """Return the percentage of default thumbnails on the page.

        """
        default_img_count = 0
        thmb_els = self.browser.find_elements_by_css_selector(self._THUMBNAIL)
        total_thumbnails = len(thmb_els)
        for thumb_el in thmb_els:
            png_file = thumb_el.get_attribute("src")
            if "nounproject_2650_television_white.png" in png_file:
                default_img_count += default_img_count
        percent_default = (default_img_count / float(total_thumbnails)) * 100
        return percent_default

    def thumbnail_count(self, expected):
        """Count the number of thumbnails dipslayed on the page.

        """
        visible_thumbs = self.count_elements_present(self._THUMBNAIL)
        if visible_thumbs is expected:
            return True
        else:
            return False, ("Found {0} thumbnail(s) on the page, expected "
                           "{1}".format(visible_thumbs, expected))

    def valid_thumbnail_sizes(self, width, height):
        """Verify thumbnails have the expected height / width attributes.

        """
        thumb_img = self._THUMBNAIL
        thumbs = self.browser.find_elements_by_css_selector(thumb_img)
        invalid_thumbs = []
        for elem in thumbs:
            size = elem.size
            if size['width'] != width or size['height'] != height:
                invalid_thumbs.append((size['width'], size['height']))
        if invalid_thumbs == []:
            return True
        else:
            return invalid_thumbs

    def has_title(self, expected):
        """Return when the the expected title is displayed.

        """
        return self.verify_text_present(self._TITLE, expected)

    def has_overlay(self, video):
        """"Return is the overlay displays and the text content.

        """
        selector = '[href="{0}"]'.format(video.get_absolute_url())
        #elem = self.browser.find_elements_by_css_selector(selector)[0]
        self.hover_by_css(selector)
        if self.is_element_present(self._HOVER):
            overlay_text = self.get_element_attribute(
                self._HOVER, 'data-content')
            return True, overlay_text

    def title_link(self, title):
        """Return the url the Title link opens.

        """
        elem = self.browser.find_element_by_link_text(title)
        return elem.get_attribute('href')

    def author_link(self, title_text, author):
        """Return the auther text and the url the link opens.

        """
        elem = self.browser.find_element_by_link_text(title_text)
        self.hover_by_css(elem)
        overlay_byline = self.get_text_by_css(self._BYLINE)
        elem = self.browser.find_element_by_link_text(author)
        return overlay_byline, elem.get_attribute('href')
