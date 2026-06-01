from io import IOBase, BytesIO
from os import path

import requests
import base64
import xmltodict




class WebDAVFile:
    def __init__(self, href:str, properties:dict) -> None:
        self.href = href
        self.filename = path.basename(p=href)
        self.properties = properties

    def __repr__(self) -> str:
        return "File: " + self.href + " - " + self.properties.__repr__()
    
class WebDAVDirectory(WebDAVFile):
    def __repr__(self) -> str:
        return "Dir:  " + self.href + " - " + self.properties.__repr__()



class WebDAVClient:
    def __init__(self,url:str,username:str="",password:str="", verbose:bool=False):
        self.url = url
        self.username = username
        self.password = password
        self.base_header = {
            "User-Agent": "Dewey-WebDAV",
            "Accept": "*/*"
        }
        self.verbose = verbose

    def _log(self, *args, verbose:bool=False):
        if (verbose and self.verbose) or not verbose:
            print(args)

    def _create_auth_string(self) -> str:
        if self.username and self.password:
            return base64.b64encode(s=f"{self.username}:{self.password}".encode()).decode()
        else:
            return ""
        
    def _make_headers(self, starting_header: dict = {}) -> dict[str,str]:
        header = starting_header

        # i think, if it was just header=self.header then it would be linked rather than a copy
        for key,value in self.base_header.items(): 
            header[key] = value

        auth = self._create_auth_string()
        if auth:
            header["Authorization"] = f"Basic {auth}"
        
        return header

    def _make_request(self, path:str, method:str, headers: dict = {}, body: str | bytes = "") -> requests.Response:
        return requests.request(method=method, url=self.url + path, headers=self._make_headers(starting_header=headers), data=body)
    
    def _xmlparse(self,data:requests.Response | str) -> dict:
        xmldata = ""

        if isinstance(data, requests.Response): 
            xmldata = data.content.decode()
        else:
            xmldata = data

        xmldict = xmltodict.parse(xml_input=xmldata,process_namespaces=True)

        return xmldict
    
    def _make_file(self, constructor: type[WebDAVFile], dict:dict) -> WebDAVFile:
        return constructor(href=dict["DAV::href"], properties=dict["DAV::propstat"]["DAV::prop"])
    


    def list(self,path:str) -> list[WebDAVFile]:
        request = self._make_request(
            path = path,
            method = "PROPFIND",
            headers = {
                "Depth": '1',
                #"Content-Type": "application/xml",
                "Accept": "application/xml"
            },
        )
        assert request.status_code == 207, f"response was \"{request.status_code}\" and not 207 Multi-Status"

        xml_listing = self._xmlparse(data=request)
        file_listing = []

        for i in xml_listing["DAV::multistatus"]["DAV::response"]:
            if i["DAV::href"][len(i["DAV::href"]) - 1] == "/": # ends with /
                file_listing.append(self._make_file(constructor=WebDAVDirectory,dict=i))
            else:
                file_listing.append(self._make_file(constructor=WebDAVFile,dict=i))

        return file_listing
    
    def download_file(self,path:str,fp:IOBase | None) -> requests.Response:
        request = self._make_request(
            path = path,
            method = "GET"
        )
        assert request.status_code == 200, f"response was \"{request.status_code}\" and not 200 OK"

        if fp:
            assert fp.writable(), "fp is not writable"

            fp.write(request.content)

        return request

    def lock_file(self, path:str):
        pass

    def unlock_file(self, path:str):
        pass

    def upload_file(self, path:str, fp:IOBase) -> requests.Response:
        request = self._make_request(
            path = path,
            method = "PUT",
            body = fp.read()
        )
        assert request.status_code in [200, 201], f"response was \"{request.status_code}\" and not 200 OK (" + request.content.decode()[:25] + ")"
        self._log(request.headers, verbose=True)
        self._log(request.content, verbose=True)

        return request

    def delete_file(self, path:str) -> requests.Response:
        request = self._make_request(
            path = path,
            method = "DELETE",
        )
        assert request.status_code in [200, 201], f"response was \"{request.status_code}\" and not 200 OK (" + request.content.decode()[:25] + ")"
        self._log(request.headers, verbose=True)
        self._log(request.content, verbose=True)

        return request
