from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle, KeepTogether

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs'/'user-manual'/'ProcureFlow_User_Manual.pdf'
ASSETS=ROOT.parents[1]/'deliverables'/'procureflow-video'/'assets'
BLUE=colors.HexColor('#123C69'); GREEN=colors.HexColor('#3F7A49'); PALE=colors.HexColor('#EDF4EF')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='PFTitle',parent=styles['Title'],fontName='Helvetica-Bold',fontSize=30,leading=35,textColor=BLUE,alignment=TA_CENTER,spaceAfter=12))
styles.add(ParagraphStyle(name='PFSub',parent=styles['Normal'],fontName='Helvetica',fontSize=13,leading=18,textColor=GREEN,alignment=TA_CENTER,spaceAfter=12))
styles.add(ParagraphStyle(name='PFH1',parent=styles['Heading1'],fontName='Helvetica-Bold',fontSize=21,leading=25,textColor=BLUE,spaceBefore=6,spaceAfter=10))
styles.add(ParagraphStyle(name='PFH2',parent=styles['Heading2'],fontName='Helvetica-Bold',fontSize=14,leading=18,textColor=GREEN,spaceBefore=7,spaceAfter=5))
styles.add(ParagraphStyle(name='PFBody',parent=styles['BodyText'],fontName='Helvetica',fontSize=10,leading=14,textColor=colors.HexColor('#20342B'),spaceAfter=6))
styles.add(ParagraphStyle(name='PFBullet',parent=styles['PFBody'],leftIndent=14,firstLineIndent=-8,bulletIndent=0))
styles.add(ParagraphStyle(name='PFCaption',parent=styles['PFBody'],fontSize=8,textColor=colors.grey,alignment=TA_CENTER,spaceAfter=9))

def footer(canvas,doc):
    canvas.saveState();canvas.setStrokeColor(GREEN);canvas.line(0.7*inch,0.55*inch,A4[0]-0.7*inch,0.55*inch);canvas.setFont('Helvetica',8);canvas.setFillColor(BLUE);canvas.drawString(0.7*inch,0.35*inch,'PROCUREFLOW  |  USER MANUAL  |  SIH26032');canvas.drawRightString(A4[0]-0.7*inch,0.35*inch,f'Page {doc.page}');canvas.restoreState()
def p(text,style='PFBody'): story.append(Paragraph(text,styles[style]))
def bullets(items):
    for x in items:p('• '+x,'PFBullet')
def nums(items):
    for i,x in enumerate(items,1):p(f'<b>{i}.</b> {x}','PFBullet')
def pic(name,caption):
    path=ASSETS/name
    if path.exists():story.append(KeepTogether([Image(str(path),width=6.8*inch,height=3.825*inch),Paragraph(caption,styles['PFCaption'])]))
def page(title):story.extend([PageBreak(),Paragraph(title,styles['PFH1'])])

doc=SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=0.7*inch,leftMargin=0.7*inch,topMargin=0.65*inch,bottomMargin=0.72*inch,title='ProcureFlow User Manual',author='ProcureFlow Team')
story=[Spacer(1,0.25*inch),Paragraph('PF',ParagraphStyle(name='Logo',fontName='Helvetica-Bold',fontSize=32,textColor=GREEN,alignment=TA_CENTER,spaceAfter=8)),Paragraph('ProcureFlow User Manual',styles['PFTitle']),Paragraph('Farmer procurement scheduling, live queue management and direct support',styles['PFSub']),Paragraph('Version 1.5  •  10 September 2026  •  Software prototype for SIH26032',styles['PFSub'])]
pic('01_title.png','ProcureFlow — a focused, multilingual procurement-service MVP')
p('This manual covers the public website, installable Android web app, automated ProcureBot assistant, farmer/staff-to-admin live chat, notifications and operational dashboards.')

page('1. Product at a glance')
p('ProcureFlow helps farmers choose a procurement centre, confirm eligibility, reserve a token, track queue wait time and follow produce through procurement and payment. Centre staff operate queues; administrators manage capacity, alerts, records and support conversations.')
data=[[Paragraph('<b>Farmer</b>',styles['PFBody']),Paragraph('<b>Centre staff</b>',styles['PFBody']),Paragraph('<b>Administrator</b>',styles['PFBody'])],[Paragraph('Book and track visits; contact support',styles['PFBody']),Paragraph('Advance queues and procurement stages',styles['PFBody']),Paragraph('Manage schedules, records, alerts and chats',styles['PFBody'])]]
t=Table(data,colWidths=[2.25*inch]*3);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),BLUE),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#CAD8D0')),('VALIGN',(0,0),(-1,-1),'TOP'),('PADDING',(0,0),(-1,-1),8)]));story.append(t)
p('<b>Demo accounts</b>','PFH2');bullets(['Farmer — farmer@demo.in / farmer123','Centre staff — staff@demo.in / staff123','Administrator — admin@demo.in / admin123']);p('<b>No ChatGPT account is required.</b> ProcureFlow uses its own demonstration role sign-in.');pic('02_access.png','Role-based ProcureFlow access screen')

page('2. Farmer journey')
p('2.1 Choose the right centre','PFH2');p('Compare nearby centres by travel distance, available slots, queue size and estimated wait. The recommendation favours the least-congested practical option.');pic('04_centres.png','Centre recommendation and congestion comparison')
p('2.2 Book a procurement token','PFH2');nums(['Open <b>Schedules</b> and select <b>Check eligibility</b>.','Choose the centre and preferred time window.','Enter quantity and confirm ID, bank and land/tenancy declarations.','Press <b>Confirm and book token</b>.']);pic('05_booking.png','Eligibility and token-booking flow')

page('3. Queue, procurement and recovery')
p('The live journey is: <b>Booked → Arrived → Gate check-in → Weighing → Quality check → Accepted → Payment processing → Payment completed.</b> Wait time changes as centre staff progress the queue.');pic('06_journey.png','Farmer-facing procurement status and estimated wait')
p('Missed-slot recovery','PFH2');p('From the active token, select <b>I missed my slot</b>. Choose the next suitable centre/time and confirm rebooking.')

page('4. ProcureBot automated assistant')
p('Open <b>Support</b> and keep <b>ProcureBot help</b> selected. The rule-based assistant answers common procurement questions instantly without an external AI account. It covers token booking, eligibility documents, queue ETA, missed slots, payment status, regional languages and escalation to an admin.')
bullets(['Use a quick-question chip for the fastest demonstration.','Type a short question such as “What documents are needed?”','For an individual case, switch to Live admin chat.'])
p('Why rule-based?','PFH2');p('The hackathon build remains predictable, free to operate and useful even when no external AI service is available.')

page('5. Live admin chat')
p('Farmers and centre staff can contact the administrator directly. The conversation displays the participant name, stores message history in the hosted database and places media in managed object storage.')
p('Send text and media','PFH2');nums(['Select <b>Live admin chat</b>.','Type a message, or press <b>＋</b> to attach a photo, short video or audio file.','For a voice note, press <b>●</b>, allow microphone access, speak, then press it again.','Press <b>Send</b>. Attachments are limited to 12 MB.'])
p('Read receipts, editing and deletion','PFH2');bullets(['<b>Sent ✓</b> means the message reached the service.','<b>Seen ✓✓</b> means the other role opened the conversation.','Edit changes your own text and marks it as edited.','Delete removes content and its attachment; admins may moderate any message.','A short chime plays for new incoming messages after page interaction.'])
p('Administrator workflow','PFH2');p('Sign in as Administrator, open <b>Live chat</b>, select a named conversation with an unread badge and reply. Opening the conversation issues the read receipt.')

page('6. Centre staff and administrator')
p('Centre staff','PFH2');p('The centre dashboard shows green/yellow/red load indicators, expected arrivals and the active queue. Use the action button to progress the selected token through every stage.');pic('08_staff.png','Centre load and live queue workflow')
p('Administrator','PFH2');p('The administrator monitors capacity and congestion, creates schedules, explores 100,000 deterministic demonstration records, sends alerts and manages live support.');pic('09_admin.png','Administrative overview')

page('7. Data and alerts')
p('Records explorer','PFH2');p('Filter 100,000 records by crop, centre and status, then sort by date, crop, quantity, wait or centre. The generated dataset is deterministic for repeatable judging.');pic('10_records.png','Filterable and sortable procurement records')
p('Notifications','PFH2');p('Enable phone alerts grants browser notification permission. A custom alert appears in-app and on the current device. The preset Twilio button demonstrates trial delivery; production custom SMS requires approved sender/template registration and compliance controls.');pic('07_alerts.png','Notification centre and farmer alerts')

page('8. Installable Android app')
p('ProcureFlow is a Progressive Web App (PWA), so the tested public website can be installed without maintaining a separate APK during the hackathon.')
nums(['Open the public HTTPS URL in Chrome on Android.','Select <b>Install app</b> when available, or Chrome menu → <b>Add to Home screen</b>.','Confirm and launch ProcureFlow from its home-screen icon.'])
p('Core screens are cached for fast reopening. Live queue data, chat, media and alerts require internet connectivity.')
p('Languages and accessibility','PFH2');p('Use the top selector for English, Hindi or Marathi. The responsive layout uses large touch targets, status colours plus text labels and mobile bottom navigation.');pic('11_language.png','Regional-language interface')

page('9. Troubleshooting and production checklist')
issues=[['Issue','Resolution'],['Chat does not load','Check internet, refresh and sign in again.'],['Microphone is blocked','Allow microphone in browser site permissions.'],['Install button is missing','Use Chrome menu → Add to Home screen.'],['No sound','Interact with the page once and check device mute.'],['Media is rejected','Use a photo/video/audio file below 12 MB.'],['Language remains English','Choose Hindi or Marathi again and refresh the route.']]
t=Table([[Paragraph(f'<b>{x}</b>' if i==0 else x,styles['PFBody']) for x in row] for i,row in enumerate(issues)],colWidths=[2*inch,4.75*inch],repeatRows=1);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),BLUE),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#CAD8D0')),('VALIGN',(0,0),(-1,-1),'TOP'),('PADDING',(0,0),(-1,-1),7)]));story.append(t)
p('Production boundaries','PFH2');p('This MVP uses demonstration identities. A rollout must integrate authoritative authentication, role authorization, consent and retention policy, attachment malware scanning, audit logs, rate limiting, backup/restore testing, accessibility review and approved messaging templates.')
p('Recommended 4-minute demonstration','PFH2');nums(['Farmer: compare centres and book a token.','Staff: progress the queue and show ETA/journey updates.','Farmer: ask ProcureBot, then send a photo or voice note.','Admin: open the named conversation, reply and show Seen ✓✓.','Install the PWA and finish with multilingual and records views.'])

doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
