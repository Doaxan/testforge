"""SheerID verification engine — API flow with TLS impersonation.

Flow (mirrors the public widget):
  1. POST /rest/v2/verification/{vid}/step/collect{Student|Teacher}PersonalInfo
  2. DELETE /step/sso                      (skip SSO when offered)
  3. POST /step/docUpload                  -> presigned S3 uploadUrl
  4. PUT  uploadUrl                        (document bytes)
  5. POST /step/completeDocUpload
  6. GET  my.sheerid.com/rest/v2/verification/{vid}   (status polling)
"""
import re
import random
import logging
from typing import Optional, Dict, Tuple

from .. import config
from . import antidetect

logger = logging.getLogger("eduforge.engine")


def parse_verification_id(url: str) -> Optional[str]:
    m = re.search(r"verificationId=([a-f0-9]{24})", url or "", re.IGNORECASE)
    if m:
        return m.group(1).lower()
    if re.fullmatch(r"[a-f0-9]{24}", (url or "").strip().lower()):
        return url.strip().lower()
    return None


def device_fingerprint() -> str:
    return "".join(random.choice("0123456789abcdef") for _ in range(32))


class SheerIDClient:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.session, self.lib, self.impersonate = antidetect.create_session(proxy=proxy)

    def _req(self, method: str, url: str, body: Optional[Dict] = None,
             raw: Optional[bytes] = None, content_type: str = "application/json") -> Tuple[object, int]:
        headers = antidetect.get_headers(for_sheerid=True)
        headers["Content-Type"] = content_type
        kwargs = {"headers": headers}
        if body is not None:
            kwargs["json"] = body
        if raw is not None:
            kwargs["data"] = raw
        resp = antidetect.make_request(self.session, method, url,
                                       impersonate=self.impersonate, **kwargs)
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        return data, resp.status_code

    def status(self, vid: str) -> Dict:
        data, code = self._req("GET", f"{config.MY_SHEERID}/rest/v2/verification/{vid}")
        if code != 200 or not isinstance(data, dict):
            return {"ok": False, "http": code, "raw": data}
        step = data.get("currentStep", "")
        return {
            "ok": True,
            "http": code,
            "currentStep": step,
            "status": config.STEP_STATUS.get(step, step or "unknown"),
            "redirectUrl": data.get("redirectUrl"),
            "errorIds": data.get("errorIds", []),
            "raw": data,
        }

    def submit_info(self, vid: str, program: Dict, identity: Dict, school: Dict) -> Dict:
        body = {
            "firstName": identity["first_name"],
            "lastName": identity["last_name"],
            "birthDate": identity.get("birth_date", ""),
            "email": identity["email"],
            "phoneNumber": identity.get("phone", ""),
            "organization": {
                "id": int(school["id"]),
                "idExtended": str(school["idExtended"]),
                "name": school["name"],
            },
            "deviceFingerprintHash": identity.get("fingerprint") or device_fingerprint(),
            "locale": identity.get("locale", "en-US"),
            "metadata": {
                "marketConsentValue": False,
                "refererUrl": f"{config.SHEERID_BASE}/verify/{program['programId']}/?verificationId={vid}",
                "verificationId": vid,
                "flags": config.FLAGS,
                "submissionOptIn": config.SUBMISSION_OPT_IN,
            },
        }
        if program["kind"] == "teacher":
            body["employeeId"] = identity.get("employee_id", "")
        data, code = self._req(
            "POST",
            f"{config.SHEERID_BASE}/rest/v2/verification/{vid}/step/{program['infoStep']}",
            body,
        )
        return {"http": code, "data": data}

    def skip_sso(self, vid: str) -> Dict:
        data, code = self._req("DELETE", f"{config.SHEERID_BASE}/rest/v2/verification/{vid}/step/sso")
        return {"http": code, "data": data}

    def request_upload(self, vid: str, filename: str, size: int, mime: str = "image/png") -> Dict:
        body = {"files": [{"fileName": filename, "mimeType": mime, "fileSize": size}]}
        data, code = self._req(
            "POST", f"{config.SHEERID_BASE}/rest/v2/verification/{vid}/step/docUpload", body)
        return {"http": code, "data": data}

    def upload_s3(self, upload_url: str, payload: bytes, mime: str = "image/png") -> bool:
        _, code = self._req("PUT", upload_url, raw=payload, content_type=mime)
        return 200 <= code < 300

    def complete_upload(self, vid: str) -> Dict:
        data, code = self._req(
            "POST", f"{config.SHEERID_BASE}/rest/v2/verification/{vid}/step/completeDocUpload")
        return {"http": code, "data": data}

    def run(self, vid: str, program: Dict, identity: Dict, school: Dict,
            doc_bytes: bytes, filename: str = "document.png",
            mime: str = "image/png", skip_sso: bool = True) -> Dict:
        """Execute the full submission flow. Returns a result dict; never raises."""
        log = []
        try:
            r = self.submit_info(vid, program, identity, school)
            log.append({"step": "info", "http": r["http"]})
            if r["http"] != 200:
                return {"success": False, "stage": "info", "detail": r["data"], "log": log}
            data = r["data"] if isinstance(r["data"], dict) else {}
            if data.get("currentStep") == "error":
                return {"success": False, "stage": "info",
                        "detail": data.get("errorIds", ["unknown"]), "log": log}
            step = data.get("currentStep", "")

            if skip_sso and step in ("sso", program["infoStep"]):
                r = self.skip_sso(vid)
                log.append({"step": "sso", "http": r["http"]})
                if isinstance(r["data"], dict):
                    step = r["data"].get("currentStep", step)

            r = self.request_upload(vid, filename, len(doc_bytes), mime)
            log.append({"step": "docUpload", "http": r["http"]})
            docs = (r["data"] or {}).get("documents") if isinstance(r["data"], dict) else None
            if not docs:
                return {"success": False, "stage": "docUpload", "detail": r["data"], "log": log}
            upload_url = docs[0]["uploadUrl"]

            if not self.upload_s3(upload_url, doc_bytes, mime):
                return {"success": False, "stage": "s3", "detail": "upload failed", "log": log}
            log.append({"step": "s3", "ok": True, "bytes": len(doc_bytes)})

            r = self.complete_upload(vid)
            log.append({"step": "complete", "http": r["http"]})
            final = r["data"] if isinstance(r["data"], dict) else {}
            return {
                "success": r["http"] == 200,
                "pending": True,
                "stage": "submitted",
                "verification_id": vid,
                "currentStep": final.get("currentStep"),
                "status": config.STEP_STATUS.get(final.get("currentStep", ""), "pending"),
                "redirectUrl": final.get("redirectUrl"),
                "log": log,
            }
        except Exception as e:
            logger.exception("engine run failed")
            return {"success": False, "stage": "exception", "detail": str(e), "log": log}