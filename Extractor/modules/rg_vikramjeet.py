import requests
import base64
import json
import cloudscraper
from pyrogram import filters
from Extractor import app
import os
import asyncio
import aiohttp
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode
from bs4 import BeautifulSoup
from config import CHANNEL_ID

log_channel = CHANNEL_ID

def decrypt(enc):
    enc = b64decode(enc.split(':')[0])
    key = '638udh3829162018'.encode('utf-8')
    iv = 'fedcba9876543210'.encode('utf-8')
    if len(enc) == 0:
        return ""

    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(enc), AES.block_size)
    return plaintext.decode('utf-8')

def decode_base64(encoded_str):
    try:
        decoded_bytes = base64.b64decode(encoded_str)
        decoded_str = decoded_bytes.decode('utf-8')
        return decoded_str
    except Exception as e:
        return f"Error decoding string: {e}"

def _base(api):
    return api if api.startswith(("http://", "https://")) else f"https://{api}"

async def fetch(session, url, headers):
    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"Error fetching {url}: HTTP {response.status}")
                return {}
            content = await response.text()
            return json.loads(str(BeautifulSoup(content, "html.parser")))
    except Exception as e:
        print(f"An error occurred while fetching {url}: {str(e)}")
        return {}

async def handle_course(session, api_base, course_id, subject_id, topic_id, headers, f):
    url = f"{api_base}/get/livecourseclassbycoursesubtopconceptapiv3?courseid={course_id}&subjectid={subject_id}&topicid={topic_id}&conceptid=&start=-1"
    r3 = await fetch(session, url, headers)
    videos = sorted(r3.get("data", []), key=lambda x: x.get("id") or 0)
    await asyncio.gather(*[fetch_item_details(session, api_base, course_id, v, headers, f, folder_wise=0) for v in videos])

async def fetch_item_details(session, api, course_id, item, headers, f, folder_wise=1):
    fi = item.get("id")
    t = item.get("Title")
    async with session.get(f"{_base(api)}/get/fetchVideoDetailsById?course_id={course_id}&folder_wise_course={folder_wise}&ytflag=0&video_id={fi}", headers=headers) as response:
        r4 = await response.json()
        vt = r4["data"].get("Title", "")
        vl = r4["data"].get("download_link", "")
        if vl:
            dvl = decrypt(vl)
            print(f"{vt}:{dvl}")
            f.write(f"{vt}:{dvl}\n")
        else:
            encrypted_links = r4["data"].get("encrypted_links", [])
            for link in encrypted_links:
                a = link.get("path")
                k = link.get("key")
                if a and k:
                    k1 = decrypt(k)
                    k2 = decode_base64(k1)
                    da = decrypt(a)
                    print(f"{vt}:{da}*{k2}")
                    f.write(f"{vt}:{da}*{k2}\n")
                    break
        if "material_type" in r4["data"]:
            mt = r4["data"]["material_type"]
            if mt == "VIDEO":
                p1 = r4["data"].get("pdf_link", "")
                p2 = r4["data"].get("pdf_link2", "")
                if p1:
                    dp1 = decrypt(p1)
                    print(f"{vt}:{dp1}")
                    f.write(f"{vt}:{dp1}\n")
                if p2:
                    dp2 = decrypt(p2)
                    print(f"{vt}:{dp2}")
                    f.write(f"{vt}:{dp2}\n")

async def fetch_folder_contents(session, api, course_id, folder_id, headers, f):
    async with session.get(f"{_base(api)}/get/folder_contentsv2?course_id={course_id}&parent_id={folder_id}", headers=headers) as response:
        j = await response.json()
        tasks = []
        if "data" in j:
            for item in j["data"]:
                mt = item.get("material_type")
                tasks.append(fetch_item_details(session, api, course_id, item, headers, f))
                if mt == "FOLDER":
                    tasks.append(fetch_folder_contents(session, api, course_id, item["id"], headers, f))
        await asyncio.gather(*tasks)

async def rgvikram_txt(app, message, api, name):
    api_base = api if api.startswith(("http://", "https://")) else f"https://{api}"
    
    editable11 = await app.send_message(message.chat.id, "Send Id*password or Token")
    input1 = await app.listen(editable11.chat.id)
    raw_text = input1.text
    await input1.delete(True)
    await editable11.delete(True)
    
    if '*' in raw_text:

        raw_url = f"{api_base}/post/userLogin"
        hdr = {
            "Auth-Key": "appxapi",
            "User-Id": "-2",
            "Authorization": "",
            "User_app_category": "",
            "Language": "en",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": "okhttp/4.9.1"
        }
        info = {"email": raw_text.split("*")[0], "password": raw_text.split("*")[1]}
        print(info)
        
        try:
            response = requests.post(raw_url, data=info, headers=hdr).json()
            userid = response["data"]["userid"]
            token = response["data"]["token"]
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return await message.reply_text("Please try again later. Maybe Password Wrong")

        hdr1 = {
            "Client-Service": "Appx",
            "source": "website",
            "Auth-Key": "appxapi",
            "Authorization": token,
            "User-ID": userid
        }
        await message.reply_text("**Login Successful✅**")
    else:
        # Login using token
        token = raw_text
        hdr1 = {
            "Client-Service": "Appx",
            "source": "website",
            "Auth-Key": "appxapi",
            "Authorization": token,
            "User-ID": ""
        }
        await message.reply_text("**Login with Token Successful✅**")
    
    try:
        mc1 = requests.get(f"{api_base}/get/get_all_purchases?userid={hdr1['User-ID']}&item_type=10", headers=hdr1).json()
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        return await message.reply_text("Error decoding response from server. Please try again later.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return await message.reply_text("An error occurred while fetching your courses. Please try again later.")
    
    FFF = "𝗕𝗔𝗧𝗖𝗛 𝗜𝗗 ➤ 𝗕𝗔𝗧𝗖𝗛 𝗡𝗔𝗠𝗘\n\n"
    
    if "data" in mc1 and mc1["data"]:
        for i in mc1["data"]:
            for ct in i["coursedt"]:
                ci = ct.get("id")
                cn = ct.get("course_name")
                FFF += f"**`{ci}`   -   `{cn}`**\n\n"
    else:
        try:
            mc2 = requests.get(f"{api_base}/get/mycourseweb?userid={hdr1['User-ID']}", headers=hdr1).json()
            if "data" in mc2 and mc2["data"]:
                for i in mc2["data"]:
                    ci = i.get("id")
                    cn = i.get("course_name")
                    FFF += f"**`{ci}`   -   `{cn}`**\n\n"
            else:
                await message.reply_text("No course found in ID")
                return
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            return await message.reply_text("Error decoding response from server. Please try again later.")
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return await message.reply_text("An error occurred while fetching your courses. Please try again later.")

    editable1 = await message.reply_text(f"𝗔𝗽𝗽𝘅 𝗟𝗼𝗴𝗶𝗻 𝗦𝘂𝗰𝗲𝘀𝘀✅\n\n`{token}`\n{FFF}")
    
    editable2 = await app.send_message(message.chat.id, "**Now send the Course ID to Download**")
    input2 = await app.listen(editable2.chat.id)
    raw_text2 = input2.text
    await editable1.delete(True)
    await editable2.delete(True)
    await input2.delete(True)
    
    try:
        r = requests.get(f"{api_base}/get/course_by_id?id={raw_text2}", headers=hdr1).json()
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        return await message.reply_text("Error decoding response from server. Please try again later.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return await message.reply_text("An error occurred while fetching the course details. Please try again later.")

    for i in r.get("data", []):
        txtn = i.get("course_name")
        filename = f"{raw_text2}_{txtn.replace(':', '_').replace('/', '_')}.txt"

        if '/' in filename:
            filename1 = filename.replace("/", "").replace(" ", "_")
        else:
            filename1 = filename

        async with aiohttp.ClientSession() as session:
            with open(filename1, 'w') as f:
                try:
                    r1 = await fetch(session, f"{api_base}/get/allsubjectfrmlivecourseclass?courseid={raw_text2}&start=-1", hdr1)
                    tasks = []
                    for i in r1.get("data", []):
                        si = i.get("subjectid")
                        sn = i.get("subject_name")
                        r2 = await fetch(session, f"{api_base}/get/alltopicfrmlivecourseclass?courseid={raw_text2}&subjectid={si}&start=-1", hdr1)
                        for i in r2.get("data", []):
                            ti = i.get("topicid")
                            tn = i.get("topic_name")
                            tasks.append(handle_course(session, api_base, raw_text2, si, ti, hdr1, f))
                    await asyncio.gather(*tasks)
                except Exception as e:
                    print(f"An error occurred while processing the course: {str(e)}")
                    return await message.reply_text("An error occurred while processing the course. Please try again later.")
        
        try:
            await app.send_document(message.chat.id, filename1)
            await app.send_document(log_channel, filename1, caption=f"{txtn}")
        except Exception as e:
            print(f"An error occurred while sending the document: {str(e)}")
            await message.reply_text("An error occurred while sending the document. Please try again later.")
        finally:
            if os.path.exists(filename1):
                os.remove(filename1)


# ---- /rgvikramjeet command (from TXT-EXTRACTOR) ----
from pyrogram import Client
from pyrogram.types import Message

@app.on_message(filters.command(["rgvikramjeet"]))
async def rgvikramjeet(bot: Client, m: Message):
    await m.reply_text("Send **ID & Password** like this: `ID*Password`")

    input1: Message = await bot.listen(m.chat.id)
    raw_text = input1.text
    userid = raw_text.split("*")[0]
    password = raw_text.split("*")[1]

    login_url = "https://appapi.videocrypt.in/data_model/users/login_auth"
    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        "Origin": "https://rankersgurukul.com",
        "Referer": "https://rankersgurukul.com/",
        "Appid": "753",
        "Devicetype": "4",
        "Lang": "1"
    }
    payload = {
        "userid": userid,
        "password": password
    }

    try:
        response = requests.post(login_url, headers=headers, json=payload)
        data = response.json()

        if "access_token" not in data:
            await m.reply_text("❌ Login failed. Please check your ID and password.")
            return

        token = data["access_token"]
        user_id = data.get("user_id") or data.get("userid")
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Get courses
        courses_url = f"https://appapi.videocrypt.in/data_model/courses?userId={user_id}"
        res_courses = requests.get(courses_url, headers=auth_headers)
        courses = res_courses.json().get("data", [])

        if not courses:
            await m.reply_text("⚠️ No courses found.")
            return

        message_text = "**📚 Your Courses:**\n\n"
        for course in courses:
            course_id = course.get("id")
            course_name = course.get("course_name") or course.get("name")
            message_text += f"`{course_id}` - **{course_name}**\n"
        await m.reply_text(message_text)

        # Ask for course ID
        await m.reply_text("Send the **Course ID** to continue:")
        input2 = await bot.listen(m.chat.id)
        selected_course = input2.text.strip()

        # Get subjects
        subjects_url = f"https://appapi.videocrypt.in/data_model/courses/subjects?courseId={selected_course}"
        res_subjects = requests.get(subjects_url, headers=auth_headers)
        subjects = res_subjects.json().get("data", [])

        subj_text = "**📘 Subjects:**\n\n"
        for subj in subjects:
            subj_id = subj.get("id")
            subj_name = subj.get("subject_name")
            subj_text += f"`{subj_id}` - **{subj_name}**\n"
        await m.reply_text(subj_text)

        # Ask for subject ID
        await m.reply_text("Send the **Subject ID**:")
        input3 = await bot.listen(m.chat.id)
        selected_subject = input3.text.strip()

        # Get topics
        topics_url = f"https://appapi.videocrypt.in/data_model/courses/subjects/topics?subjectId={selected_subject}&courseId={selected_course}"
        res_topics = requests.get(topics_url, headers=auth_headers)
        topics = res_topics.json().get("data", [])

        topic_text = "**📝 Topics:**\n\n"
        for topic in topics:
            topic_id = topic.get("id")
            topic_name = topic.get("topic_name")
            topic_text += f"`{topic_id}` - **{topic_name}**\n"
        await m.reply_text(topic_text)

        # Ask for topic ID(s)
        await m.reply_text("Send one or more **Topic IDs** (separated by &):")
        input4 = await bot.listen(m.chat.id)
        topic_ids = input4.text.strip().split("&")

        # Ask for resolution (if needed)
        await m.reply_text("Now send the **Resolution** (or type 'any'):")
        input5 = await bot.listen(m.chat.id)
        resolution = input5.text.strip()

        download_links = []
        for topic_id in topic_ids:
            video_url = f"https://appapi.videocrypt.in/data_model/courses/videos?topicId={topic_id}&courseId={selected_course}"
            res_videos = requests.get(video_url, headers=auth_headers)
            videos = res_videos.json().get("data", [])
            for video in videos:
                title = video.get("Title")
                enc_link = video.get("download_link") or video.get("pdf_link")
                if enc_link:
                    try:
                        key = "638udh3829162018".encode("utf8")
                        iv = "fedcba9876543210".encode("utf8")
                        ciphertext = bytearray.fromhex(b64decode(enc_link.encode()).hex())
                        cipher = AES.new(key, AES.MODE_CBC, iv)
                        plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
                        decrypted_link = plaintext.decode('utf-8')
                        download_links.append(f"{title}: {decrypted_link}")
                    except Exception as e:
                        download_links.append(f"{title}: Failed to decrypt")

        filename = f"Rgvikramjeet_{selected_course}.txt"
        with open(filename, 'w') as f:
            for line in download_links:
                f.write(f"{line}\n")

        await m.reply_document(filename)
        await m.reply_text("✅ Done")

    except Exception as e:
        await m.reply_text(f"❌ Error occurred: {e}")
