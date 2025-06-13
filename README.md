# read_4me_bot
Brief Description:
The reading bot allows users to upload books in various formats (PDF, EPUB, TXT, HTML, DOCX) or via links, read them in parts, convert text to speech, schedule automatic part delivery, and manage their library. Features include voice selection for text-to-speech and a web app for convenient reading.

Detailed Description:

**Book Upload** (/uploadtext or "Upload Text" button):
Users can upload book files (PDF, EPUB, TXT, HTML, DOCX) or send a webpage link.
Limit: up to 5 books per user. To add a new book beyond this limit, an existing one must be deleted.
Uploaded books are automatically selected for reading.

**Book Reading** ("Forward", "Backward", "Read Now" buttons):
Books are split into parts (up to 4000 characters). Users can navigate parts forward or backward.
The current book and part are remembered until another book is selected or uploaded.
The "Read Now" function sends the current part.

**Text-to-Speech** (/tts or "Voice Text" button):
The current part can be converted to audio using the selected voice.
Available voices: Alloy, Echo, Fable, Nova, Onyx, Shimmer, Coral, Verse, Ballad, Ash, Sage, Amuch, Dan.
Original text from the database is used for audio generation.

**Voice Selection** (/setvoice):
Users choose a text-to-speech voice from a list via inline buttons.

**Reading Schedule** (/schedule or "Schedule" button):
Allows setting automatic part delivery at specified times (e.g., from 09:00 to 18:00 every 2 hours).
Requires specifying start time, end time, and interval.

**Book Selection** (/selectbook or "Select Book" button):
Displays a list of uploaded books for selection. The chosen book becomes the current one.

**Book Deletion** (/deletebook or "Delete Book" button):
Users can remove a book from their library via inline buttons.

**Upload Management** ("Upload Management" button):
A separate menu with "Upload Text", "Delete Book", and "Back" buttons for library management.

**Web Application** (/webapp or "Open Web App" button):
Opens a web interface for reading books, navigating parts, and requesting text-to-speech.
