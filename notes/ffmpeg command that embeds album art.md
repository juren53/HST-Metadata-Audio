## ffmpeg command that embeds album art.md

readable by WMP

ffmpeg -i input.mp3 -i album_art.jpg -map 0 -map 1 -c copy -id3v2_version 3 -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (Front)" output.mp3


To embed album art in an MP3 file using FFmpeg in a way that is compatible with Windows Media Player, you can follow these steps:

Ensure you have the album art image file (e.g., album_art.jpg) ready.

Use FFmpeg to embed the album art into the MP3 file. You can do this with the -i option to specify the input MP3 file, and the -i option again to specify the album art image file. Then, use the -map option to map the album art image to the APIC (Attached Picture) tag in the MP3 file. Finally, specify the output MP3 file.

Here's the command:

bash
ffmpeg -i input.mp3 -i album_art.jpg -map 0 -map 1 -c copy -id3v2_version 3 -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (Front)" output.mp3

Replace input.mp3 with the name of your input MP3 file, and album_art.jpg with the name of your album art image file. Ensure that output.mp3 is the desired name for your output MP3 file.

This command will copy both the audio and the album art into the output file without re-encoding (-c copy). It also sets the ID3v2 version to 3 (-id3v2_version 3), which is widely supported by media players including Windows Media Player.

Once you run this command, the album art should be embedded in the output MP3 file and should display correctly when played in Windows Media Player.


