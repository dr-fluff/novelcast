from .base import RssFeed

class RoyalRoadRss(RssFeed):
    def __init__(self):
        self.base_link = "https://www.royalroad.com/fiction/syndication/"
        self.feed = None
        
        self.create_link
    
    def create_link(self, ids: list):
        
        
        # https://www.royalroad.com/fiction/syndication/33844,72301
        
        '''
        for storys in auto update
        add id to link with ,
        
        '''
    
    def read_rss(self):
        pass    

    
    def parse_feed(self):
        pass