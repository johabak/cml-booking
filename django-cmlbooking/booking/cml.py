import requests
from time import sleep
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import os
import base64
from django.template.loader import render_to_string
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition, ContentId
from django.conf import settings
import logging
logger = logging.getLogger(__name__)
import mimetypes
from django.core.mail import EmailMultiAlternatives
from anymail.exceptions import AnymailError

def GetToken(username, password):
    """
    Authenticate with username and password and get API token

    Status codes:
      Success: 200
      Failure: 403
    """
    api_url = "authenticate"
    payload = { "username": username, "password": password }
    r = requests.post(settings.CML_API_BASE_URL+api_url, json=payload, verify=False)
    logger.info(f"GetToken: {r.status_code}")
    token = r.text.strip().strip('"').strip("'")
    return token, r.status_code

def GetListOfAllLabs(token):
    """
    Return a list of all labs

    Status codes:
      Success: 200
      Failure: any other values
    """
    api_url = "labs?show_all=true"
    head = {'Authorization': f'Bearer {token}'}
    r = requests.get(settings.CML_API_BASE_URL+api_url, headers=head, verify=False)
    logger.info(f"GetListOfAllLabs: {r.status_code}")
    return r.json(), r.status_code

def GetNodesInLab(token, labId):
    """
    Return a list of all nodes in a given lab

    Status codes:
      Success: 200
      Failure: any other values
    """
    api_url = f"labs/{labId}/nodes?data=false"
    head = {'Authorization': f'Bearer {token}'}
    r = requests.get(settings.CML_API_BASE_URL+api_url, headers=head, verify=False)
    logger.info(f"GetNodesInLab: {r.status_code}")
    return r.json(), r.status_code

def GetNodeConfig(token, labId, node):
    """
    Extract node config for a given node in a given lab

    Status codes:
      Success: 200
      Failure: any other values
    """
    api_url = f"labs/{labId}/nodes/{node}/extract_configuration"
    head = {'Authorization': f'Bearer {token}'}
    r = requests.put(settings.CML_API_BASE_URL+api_url, headers=head, verify=False)
    logger.info(f"GetNodeConfig: {r.status_code}")
    return r.json(), r.status_code

def DownloadLab(token, labId):
    """
    Download a given lab

    Status codes:
      Success: 200
      Failure: any other values
    """
    api_url = f"labs/{labId}/download"
    head = {'Authorization': f'Bearer {token}'}
    r = requests.get(settings.CML_API_BASE_URL+api_url, headers=head, verify=False)
    logger.info(f"DownloadLab: {r.status_code}")
    return r.text, r.status_code

def SaveLab(labId, labFile):
    """
    Save a given lab to file
    """
    labs_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'labs/')
    if not os.path.isdir(labs_directory):
        os.mkdir(labs_directory)
    with open(f'{os.path.join(labs_directory, labId)}.yaml', 'w') as file:
        file.write(labFile)
    logger.info(f"SaveLab: {labId}")

def StopLab(token, labId):
    """
    Stop a given lab

    Status codes:
      Success: 204
      Failure: any other values
    """
    api_url = f"labs/{labId}/stop"
    head = {'Authorization': f'Bearer {token}'}
    r = requests.put(settings.CML_API_BASE_URL+api_url, headers=head, verify=False)
    logger.info(f"StopLab: {r.status_code}")
    return r.status_code

def WipeLab(token, labId):
    """
    Wipe a given lab

    Status codes:
      Success: 204
      Failure: any other values
    """
    api_url = f"labs/{labId}/wipe"
    head = {'Authorization': f'Bearer {token}'}
    r = requests.put(settings.CML_API_BASE_URL+api_url, headers=head, verify=False)
    logger.info(f"WipeLab: {r.status_code}")
    return r.status_code

def DeleteLab(token, labId):
    """
    Delete a given lab

    Status codes:
      Success: 204
      Failure: any other values
    """
    api_url = f"labs/{labId}"
    head = {'Authorization': f'Bearer {token}'}
    r = requests.delete(settings.CML_API_BASE_URL+api_url, headers=head, verify=False)
    logger.info(f"DeleteLab: {r.status_code}")
    return r.status_code

def GetAdminId(token):
    api_url = "users/admin/id"
    head = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    r = requests.get(settings.CML_API_BASE_URL + api_url, headers=head, verify=False, timeout=10)
    logger.info(f"GetAdminId: {r.status_code} body={r.text[:200]}")
    admin_id = None
    try:
        data = r.json()
        if isinstance(data, dict) and "id" in data:
            admin_id = data["id"]
        elif isinstance(data, str):
            admin_id = data.strip().strip('"').strip("'")
    except Exception:
        # Enkel fallback hvis API ga ren tekst
        admin_id = r.text.strip().strip('"').strip("'")
    return admin_id, r.status_code

def LogAllUsersOut(token):
    """
    Clears sessions and log out everyone

    Status codes:
      Success: 200
      Failure: 401 / any other values
    """
    api_url = "logout?clear_all_sessions=true"
    head = {'Authorization': f'Bearer {token}'}
    r = requests.delete(settings.CML_API_BASE_URL+api_url, headers=head, verify=False)
    logger.info(f"LogAllUsersOut: {r.status_code}")
    return r.status_code

def UpdateUserPassword(token, userId, oldpw, newpw):
    """
    Update a user's password via the documented endpoint:
      PATCH /users/{user_id}

    Notes:
    - For admin users the API allows setting a new password by providing an
      empty old password. Therefore the 'oldpw' argument is intentionally not
      used in the payload below.
    - We try WITHOUT trailing slash first (as per docs). If that returns 404,
      we retry WITH a trailing slash for compatibility with some deployments.

    Returns: HTTP status code from the final API call.
    """

    base = settings.CML_API_BASE_URL.rstrip('/')

    # Common headers for both primary and fallback calls
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }

    # Admin path: empty old_password is allowed by the API
    payload = {"password": {"old_password": "", "new_password": newpw}}

    # 1) No trailing slash (preferred by docs)
    url = f"{base}/users/{userId}"
    r = requests.patch(url, headers=headers, json=payload, verify=False, timeout=10)
    logger.info(f"UpdateUserPassword -> {url} : {r.status_code} {r.text[:200]}")
    if r.status_code != 404:
        return r.status_code

    # 2) Retry with trailing slash (compat)
    url2 = url + "/"
    r2 = requests.patch(url2, headers=headers, json=payload, verify=False, timeout=10)
    logger.info(f"UpdateUserPassword (trailing slash) -> {url2} : {r2.status_code} {r2.text[:200]}")
    return r2.status_code

#def SendEmail(email, title, content, attachments=None):
#    """
#    Sends an email with input title and content. Attachment is optional.
#
#    Status codes:
#      Success: 202
#      Failure: any other values
#    """
#    # Create message
#    message = Mail(
#        from_email=settings.SENDGRID_FROM_EMAIL,
#        to_emails=email,
#        subject=title,
#        html_content=content)
#
#    # Add BCC if configured
#    if (settings.SENDGRID_BCC_EMAIL):
#        # Do not BCC if email and BCC is equal
#        if email != settings.SENDGRID_BCC_EMAIL:
#            message.add_bcc(settings.SENDGRID_BCC_EMAIL)
#
#    # If there are any attachment to be sendt
#    if attachments:
#        for file in attachments:
#            # Remove path from filename
#            filename = file.split('/')[-1]
#
#            # Verify that the file exists. If not, ignore
#            if os.path.exists(file):
#                # Read file
#                with open(file, 'rb') as f:
#                    data = f.read()
#                    f.close()
#                
#                # Create attachment
#                file = Attachment()
#                file.file_content = FileContent(base64.b64encode(data).decode())
#                file.file_type = FileType('text/plain')
#                file.file_name = FileName(filename)
#                file.disposition = Disposition('attachment')
#                file.content_id = ContentId(filename)
#
#                # Attach to message
#                message.attachment = file
#
#    try:
#        sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
#        response = sendgrid_client.send(message)
#        logger.info(f"SendEmail: Sending email to {email} with subject {title}.")
#        logger.info(f"SendEmail: SendGridAPI status code: {response.status_code}")
#        return response.status_code
#    except Exception as e:
#        logger.error(f"SendEmail: Failed to send email")
#        logger.info(f"SendEmail: SendGridAPI status code: {response.status_code}")
#        logger.debug(f"SendEmail: Exception: {e}")
#        return response.status_code

def SendEmail(email, title, content, attachments=None, reply_to=None, bcc_email=None, tags=None):

        """
        Sender epost via Django + Anymail (Brevo)
        - email: str | list[str]  (mottaker(e))
        - title: subject
        - content: HTML-innhold
        - attachments: liste av filstier (valgfr)

        Returns True or False.
        """

        try:
                to_list = [email] if isinstance(email, str) else list(email)


                #The mail (text as fallback)
                text_fallback = "Denne e-posten har HTML-innhold. Åpne i en HTML-kompatibel klient."
                msg = EmailMultiAlternatives(
                        subject=title,
                        body=text_fallback,
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                        to=to_list,
                        bcc=[bcc_email] if bcc_email and bcc_email not in to_list else None,
                        reply_to=[reply_to] if isinstance(reply_to, str) else reply_to,
                )
                msg.attach_alternative(content, "text/html")

                bcc = getattr(settings, "ANYMAIL_BCC_EMAIL", None)
                if bcc and (bcc not in to_list):
                        msg.bcc = [bcc]

                #Attachment
                if attachments:
                        for path in attachments:
                                if not os.path.exists(path):
                                        logger.warning(f"SendEmail: Vedlegg finnes ikke: {path}")
                                        continue
                                filename = os.path.basename(path)
                                mime, _ = mimetypes.guess_type(filename)
                                mime = mime or "application/octet-stream"
                                with open(path, "rb") as f:
                                        data = f.read()
                                msg.attach(filename, data, mime)


                sent = msg.send()
                if sent == 1:
                        logger.info(f"SendEmail OK -> to={to_list} subj='{title}' tags={tags}")
                        return True
                else:
                        logger.error(f"SendEmail: msg.send() returned {sent} (expected 1)")
                        return False
        except AnymailError as e:
                logger.exception(f"SendEmail: Anymail/Brevo-errror: {e}")
                return False
        except Exception as e:
                logger.exception(f"SendEmail: error: {e}")
                return False


def CleanUp(email, temp_password):
    """
    Clean up labs when timeslot has reached the end
    """
    # Authenticate and get all labs
    logger.info(f"CleanUp: Starting cleanup")

    # Try to authenticate with the temporary password first.
    token, statuscode = GetToken(settings.CML_USERNAME, temp_password)
    used_pw = temp_password  # Track which password was effectively used.

    # If temp login failed (e.g. temp was never set), fall back to the original admin password.
    if statuscode != 200 or not token:
        logger.warning("CleanUp: temp password login failed, retrying with original admin password")
        token, statuscode = GetToken(settings.CML_USERNAME, settings.CML_PASSWORD)
        used_pw = settings.CML_PASSWORD

    error_trace = []

    # Authenticated
    if not statuscode == 200:
        logger.error(f"CleanUp: GetToken FAILED! Not authenticated!")
        error_trace.append("01: GetToken failed! Not authenticated!")
        if (settings.SENDGRID_BCC_EMAIL):
            SendEmail(settings.SENDGRID_BCC_EMAIL, 'Community Network - CleanUp failed!', f'CleanUp failed. Error reason: { error_trace }')
        return
    else:
        labs, statuscode = GetListOfAllLabs(token)
        
        # Loop through all labs, save config, stop and delete labs
        userlabs = []
        for lab in labs:
            nodes, statuscode = GetNodesInLab(token, lab)
            if not statuscode == 200:
                logger.error(f"CleanUp: GetNodesInLab FAILED for {lab}")
                error_trace.append(f"02: GetNodedInLab failed for {lab}")
            else:
                for node in nodes:
                    # Note! Extract of config only works if node is running,
                    #       so non-running nodes will not be part of lab export
                    nodeconfig, statuscode = GetNodeConfig(token, lab,node)
                    if not statuscode == 200:
                        logger.error(f"CleanUp: GetNodeConfig FAILED for {node}")
                        error_trace.append(f"03: GetNodeConfig failed for {node}")

                # Append lab to list of labs
                userlabs.append(lab)

                # Download and save lab
                downloadlab, statuscode = DownloadLab(token, lab)
                if statuscode == 200:
                    SaveLab(lab, downloadlab)
                else:
                    logger.error(f"CleanUp: DownloadLab FAILED for lab {lab}.")
                    error_trace.append(f"04: DownloadLab failed for {lab}")
                
                # Stop, wipe and delete lab
                statuscode = StopLab(token, lab)
                if statuscode != 204:
                    # Correct logging: StopLab failed here.
                    logger.error(f"CleanUp: StopLab FAILED for lab {lab}.")
                    error_trace.append(f"05: StopLab failed for {lab}")                
                else:
                    statuscode = WipeLab(token, lab)
                    if statuscode != 204:
                        logger.error(f"CleanUp: WipeLab FAILED for lab {lab}.")
                        error_trace.append(f"05: WipeLab failed for {lab}")

                statuscode = DeleteLab(token, lab)
                if not statuscode == 204:
                    logger.error(f"CleanUp: DeleteLab FAILED for lab {lab}.")
                    error_trace.append(f"06: DeleteLab failed for {lab}")
        
        # Get admin id
        adminid, statuscode = GetAdminId(token)
        if not statuscode == 200:
            error_trace.append("07: GetAdminId failed!")
            logger.error(f"CleanUp: GetAdminId FAILED!")
        else:
            # Reset password
            statuscode = UpdateUserPassword(token, adminid, temp_password, settings.CML_PASSWORD)

            if not statuscode == 200:
                error_trace.append("08: UpdateUserPassword failed!")
                logger.error(f"CleanUp: UpdateUserPassword FAILED!")
            else:
                # Only attempt to restore if the temp password was actually active (i.e., we logged in with it).
                if used_pw == temp_password:
                    statuscode = UpdateUserPassword(token, adminid, temp_password, settings.CML_PASSWORD)
                    if not statuscode == 200:
                        error_trace.append("08: UpdateUserPassword failed!")
                        logger.error(f"CleanUp: UpdateUserPassword FAILED!")
                    else:
                        # Password restored OK → re-authenticate and log out all users (clear sessions)
                        token, statuscode = GetToken(settings.CML_USERNAME, settings.CML_PASSWORD)
                        if not statuscode == 200:
                            error_trace.append("09: GetToken FAILED after changing password!")
                            logger.error(f"CleanUp: GetToken FAILED after changing password!")
                        else:
                            statuscode = LogAllUsersOut(token)
                            if not statuscode == 200:
                                error_trace.append("10: LogAllUsersOut FAILED after changing password!")
                                logger.error(f"CleanUp: LogAllUsersOut FAILED after changing password!")
                else:
                    logger.info("CleanUp: No password restore needed (temp password was never active).")

                # Loop through the labs and create list of attachments, if any
                attachments = []
                if userlabs:
                    for lab in userlabs:
                        labs_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'labs/')
                        attachments.append(f'{labs_directory}{lab}.yaml')

                # Send the user an email (with attachments, if any) using template
                context = {
                    'cml_url': settings.CML_URL,
                    'booking_url': settings.BOOKING_URL,
                }
                body = render_to_string('booking/email_teardown.html', context)
                ok = SendEmail(email, 'Community Network - CML reservasjon er utløpt', body, attachments)
                if not ok:
                    error_trace.append("11: SendEmail FAILED after cleanup!")
                    logger.error(f"CleanUp: SendEmail FAILED after cleanup!")

    if error_trace:
        # Something failed! Lets drop the admin an email
        if (settings.SENDGRID_BCC_EMAIL):
            SendEmail(settings.SENDGRID_BCC_EMAIL, 'Community Network - CleanUp failed!', f'CleanUp failed. Error reason: { error_trace }')

def CreateTempUser(email, temp_password):
    """
    Create an temporary password and send the credentials via email
    """
    logger.info(f"CreateTempUser: Creating user for {email}")
    error_trace = []

    # Get token and update username
    token, statuscode = GetToken(settings.CML_USERNAME, settings.CML_PASSWORD)
    
    if statuscode != 200 or not token:
        logger.error(f"CreateTempUser: GetToken FAILED! Not authenticated!")
        error_trace.append("01: GetToken failed! Not authenticated!")
    else:
        # Authentication OK! Lets get the Admin ID
        adminid, statuscode = GetAdminId(token)
        if not statuscode == 200:
            logger.error(f"CreateTempUser: GetAdminId FAILED!")
            error_trace.append("02: GetAdminId failed!")
        else:
            statuscode = UpdateUserPassword(token, adminid, settings.CML_PASSWORD, temp_password)
            if not statuscode == 200:
                logger.error(f"CreateTempUser: UpdateUserPassword FAILED!")
                error_trace.append("03: UpdateUserPassword failed!")
            else:
                # Send email to the user with the login information using template
                context = {
                    'username': settings.CML_USERNAME,
                    'password': temp_password,
                    'cml_url': settings.CML_URL,
                    'booking_url': settings.BOOKING_URL,
                }
                body = render_to_string('booking/email_setup.html', context)

 #               statuscode = SendEmail(email, 'Community Network - CML påloggingsinformasjon', body)
 #               if not statuscode == 202:
                ok = SendEmail(email, 'Community Network - CML påloggingsinformasjon', body)
                if not ok:
                    error_trace.append("04: SendEmail FAILED after creating user!")
                    logger.error(f"CreateTempUser: SendEmail FAILED after creating user!")
    
    if error_trace:
        # Send email to the user informing that something failed...
        context = {
            'cml_url': settings.CML_URL,
            'booking_url': settings.BOOKING_URL
        }
        body = render_to_string('booking/email_error.html', context)

        #statuscode = SendEmail(email, 'Community Network - CML - Noe gikk galt...', body)
        #if not statuscode == 202:
        ok2 = SendEmail(email, 'Community Network - CML - Noe gikk galt...', body)
        if not ok2:
            error_trace.append("05: SendEmail FAILED when sending error email to user!")
            logger.error(f"CreateTempUser: SendEmail FAILED when sending error email to user!")

        # Lets drop the admin an email as well
        if (settings.SENDGRID_BCC_EMAIL):
            SendEmail(settings.SENDGRID_BCC_EMAIL, 'Community Network - CreateTempUser failed!', f'CreateTempUser failed. Error reason: { error_trace }')
