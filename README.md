# IShowHacker's Hackathon Project

Hello! Our team has chosen to solve the first problem (Data Privacy Protector).

## How To Start the App?

You can follow the steps below to get this project started:

## To run frontend:

0) Move to frontend directory
```bash
cd frontend
```

1) Install required package
```bash
npm install
```

2) Start the frontend
```bash
npm start
```

### To run backend:

0) Move to backend directory
```bash
cd backend
```

1) Install virtual environment.
```bash
pip install virtualenv
```

2) Setup python virtual environment
```bash
python -m venv env

#or 

py -m venv env
```

3) Then, switch to that env
```bash
source env/bin/activate   # on macOS/Linux
env\Scripts\activate     # on Windows
```

4) Install require packages
```bash
pip install -r requirements.txt
```

5) Run backend program
```bash
python ./run.py

#or

py ./run.py
```

## Chosen Problem Statement

### 1) Data Privacy Protector

Organizations today face a significant challenge in managing and sharing sensitive data while adhering to stringent data privacy regulations and maintaining individual privacy. The risk of exposing Personally Identifiable Information (PII) during data exchange or storage can lead to severe reputational damage, financial penalties, and a loss of customer trust. Our solution addresses this critical need by providing a robust and intuitive platform for the secure anonymization and de-anonymization of PII across various data types.

## Explanation of the Solution
Our solution, a user-friendly data privacy management platform, empowers organizations to confidently handle sensitive information by streamlining the process of PII detection, anonymization, and secure sharing. At its core, the system provides a centralized dashboard designed for ease of use and comprehensive control over data privacy.

### Key Features and Functionality:

### 1) Intuitive Partner Management
The platform begins with a simple, yet powerful, partner management system. Users can easily add new partners, each with a customizable profile. This includes selecting an icon for visual identification, defining specific PII detection settings (e.g., detecting Person names, IC Numbers, Passports, Emails, Addresses, Phone Numbers, Bank Numbers, Credit Cards), and establishing unique security parameters like a data encryption key and a file password. These granular settings ensure that PII detection and anonymization are tailored to the specific requirements and data types shared with each partner, enhancing security and compliance.

### 2)Streamlined File Upload and PII Review
Within each partner's dedicated section, users gain access to comprehensive file management capabilities. This includes the ability to upload various file types, such as .txt and .xlsx, which are then automatically scanned for PII based on the pre-configured detection settings for that specific partner. Crucially, before any anonymization occurs, the system presents a "Review Before Anonymization" pop-up. This feature displays all detected PII, its entity type (e.g., PERSON, PHONE_NUMBER, CREDIT_CARD), and a PII confidence score. Users have the critical option to interactively review this information, choosing to "ignore" specific data points if they are not to be anonymized, or to "proceed" with the identified PII. This human-in-the-loop validation step ensures accuracy and prevents unintended anonymization.

### 3) Dynamic Data State Management and Accessibility
Upon proceeding, the processed file is seamlessly integrated into a dynamic table view, providing a clear overview of all managed data. Each entry in the table displays essential information: Filename, File Type, and a crucial "State" indicator, showing whether the file is "Anonymized" or "De-anonymized." This real-time status allows users to instantly understand the privacy posture of their data. Furthermore, the table provides direct access to an "Audit Log" for detailed review and a "Download Link," enabling users to retrieve the file in its current state, whether anonymized for sharing or de-anonymized for internal use.

### 4) Comprehensive Audit Logging for Transparency
The "Audit Log" feature offers unparalleled transparency and accountability. By clicking on the log icon next to a file, users can access a comprehensive record of its processing. This log details key information such as the filename, the intended partner, the anonymization method applied (e.g., Encryption), and the original file type (e.g., text file, tabular format). Most importantly, the audit log provides a summary of the PII detection, including a breakdown of the types of PII found and the total count, offering a clear and verifiable trail of data handling.
This multi-faceted approach ensures that our solution provides a secure, flexible, and auditable framework for managing sensitive data, empowering organizations to meet their data privacy obligations with confidence.

## Tech Stack Used

Frameworks:
1) React (JavaScript) and HTML/CSS as a frontend.
2) Flask (Python) as a backend solution.

Tools:
1) VSCode as an IDE.
2) Cursor as an AI.

## Demonstration's Video Link

https://drive.google.com/file/d/1XOV-uVVgRWr_PQVjT66hMQWW4qP-_mGB/view?usp=drive_link

## Presentation Deck's Link

https://www.canva.com/design/DAGubkhJPbs/bORxkp2D9AlBO2rPkCGcQQ/view?utm_content=DAGubkhJPbs&utm_campaign=designshare&utm_medium=link2&utm_source=uniquelinks&utlId=he9e29fe0b4#1


