
__author__ = 'Anoushka'

from check_link import check_link
from check_type import check_type
from disciplines_known import disciplinesKnown
from resourceTypes import resourceTypesKnown
from visible import visible
import tldextract
from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.error import URLError
from urllib.parse import urljoin
from Organization import Organization, generic_terms
import re


class Resource:
    def __init__(self, url):
        link_status = check_link(url)
        if link_status is "working":
            self.link = url
            self.status = link_status
        else:
            print("Error with url.")
            self.status = link_status
            print(self.status)
            print("Please check your link (perhaps use http://www...) and try again")
            exit()

    text = ""
    title = "No title"
    status = "No status"
    resource_types = ""
    themes = ""
    org = "No organization found"
    validated = False
    resource_contact_person_name = "No contact individual found"
    resource_contact_org = "No contact org"
    resource_contact_email = "No contact email"
    resource_contact_phone = "No contact phone"
    links_found = []

    def get_org(self):
        return self.org.name

    def get_resource_data(self):
        self.build_title()
        self.find_resource_types()
        self.find_themes()
        self.find_organization()
        self.find_contact_info()

    def build_title(self):
        page_text = BeautifulSoup(urlopen(self.link).read())
        title = page_text.find('title', text=True)
        if title is not None:
            if title.has_attr('string'):
                no_generics = re.sub(generic_terms, '', title.string)
                self.title = re.sub('[^a-zA-Z0-9 -]', '', no_generics)
            else:
                no_generics = re.sub(generic_terms, '', title.text)
                self.title = re.sub('[^a-zA-Z0-9 -]', '', no_generics)
        else:
            self.title = 'No title'

    def find_links(self):
        if self.status is "working":
            try:
                soup = BeautifulSoup(urlopen(self.link, timeout=7).read())
                for link_tag in soup.find_all('a', href=True):
                    if check_link(link_tag['href']) is not "working":
                        new_url = urljoin(self.link, link_tag['href'])
                        if check_link(new_url) is "working" and new_url != self.link:
                            if new_url not in self.links_found:
                                self.links_found.append(new_url)
                    else:
                        if link_tag['href'] != self.link:
                            if link_tag['href'] not in self.links_found:
                                self.links_found.append(link_tag['href'])
            except URLError as e:
                self.status = "{} {} {}".format(self.link, e.reason)

    def get_base(self):
        ext_url = tldextract.extract(self.link)
        base = "http://" + ext_url.subdomain + "." + ext_url.domain + "." + ext_url.suffix
        return base

    def find_contact_info(self):
        page = BeautifulSoup(urlopen(self.link).read())
        contact = page.find('a', text=re.compile('(C|c)ontact.*'))
        if contact is not None:
            if contact.has_attr('href'):
                if check_link(contact['href']) is "working":
                    page = BeautifulSoup(urlopen(contact['href']))
                else:
                    base = self.get_base()
                    link = urljoin(base, contact['href'])
                    if check_link(link) is "working":
                        page = BeautifulSoup(urlopen(link).read())
        # first look for tag with class = phone
        phone = page.find({'class': 'phone'})
        if phone is not None:
            self.resource_contact_phone = phone.text
        else:
            # if not class = phone, look for phone number
            phone = page.find(text=re.compile('\+(9[976]\d|8[987530]\d|6[987]\d'
                                              '|5[90]\d|42\d|3[875]\d|2[98654321]'
                                              '\d|9[8543210]|8[6421]|6[6543210]|5'
                                              '[87654321]|4[987654310]|3[9643210]'
                                              '|2[70]|7|1)\s*(\(\d+\)|\d+)(\s|-)[0-9]+(-*)[0-9]+'))
            if phone is not None:
                self.resource_contact_phone = phone.strip()
        email = page.find({'class': 'email'})
        if email is not None:
            self.resource_contact_email = email.text
        else:
            email = page.find(text=re.compile('[A-Za-z0-9-._]+(@|\(at\)| at )+[A-Za-z0-9-._]+\.[A-Za-z0-9-._]+'))
            if email is not None:
                self.resource_contact_email = email

    def find_organization(self):
        # search home page
        soup = BeautifulSoup(urlopen(self.link).read())
        home = soup.find('a', {'href': '/index.php'})
        if home is None:
            home = soup.find('a', text=re.compile('(H|h)ome'))
        if home is None or not home.has_attr('href'):
            self.org = Organization("No organization found")
        else:
            home_url = urljoin(self.get_base(), home['href'])
            homepage = BeautifulSoup(urlopen(home_url).read())
            org = homepage.find('title').text
            self.org = Organization(org)
            self.org.validate_in_viaf()

    def find_themes(self):
        disciplines_found = []
        set_of_disciplines = set()
        if check_type(self.link) is "FTP":
            return "None"
        if check_type(self.link) is "HTTP":
            souper = BeautifulSoup(urlopen(self.link).read())
            # Search for all keywords, the values of the Domains dict
            for key in disciplinesKnown:
                for v in disciplinesKnown.get(key):
                    # For all keywords found, filter so that only
                    # the keywords in the page's visible text are found
                    texts = souper.find_all(text=re.compile(v))
                    visible_texts = filter(visible, texts)
                    # For every keyword (value) found, add the Domain from our
                    # dictionary (key) to the list fo domains associated with
                    # the resource
                    for vis in visible_texts:
                        # Added as a set to avoid duplicates
                        set_of_disciplines.add(key)
            # Turn the set of domains back into a list
            disciplines_found = list(set_of_disciplines)
        if len(disciplines_found) > 0:
            return " - ".join(disciplines_found)
        else:
            return 'No disciplines found'

    def find_home_page(self):
        ext = tldextract.extract(self.link)
        ext_dom = ext.domain
        ext_suff = ext.suffix
        new_url = "http://www." + ext_dom + "." + ext_suff
        new_url = new_url.strip('/')
        return new_url

    def find_resource_types(self):
        set_of_resources = set()
        souper2 = BeautifulSoup(urlopen(self.link).read())
        for key in resourceTypesKnown:
            for v in resourceTypesKnown.get(key):
                texts = souper2.find_all(text=re.compile(v))
                visible_texts = filter(visible, texts)
                for vis in visible_texts:
                    set_of_resources.add(key)
        resos_found = list(set_of_resources)
        if len(resos_found) > 0:
            self.resource_types = " - ".join(resos_found)
