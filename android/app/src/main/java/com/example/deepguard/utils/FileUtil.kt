package com.example.deepguard.utils

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.provider.OpenableColumns
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream

object FileUtil {

    val ALLOWED_IMAGE_EXTENSIONS = setOf(".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif")
    const val MAX_IMAGE_SIZE_BYTES = 20L * 1024 * 1024 // 20 MB

    val ALLOWED_VIDEO_EXTENSIONS = setOf(".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv")
    const val MAX_VIDEO_SIZE_BYTES = 500L * 1024 * 1024 // 500 MB

    val ALLOWED_AUDIO_EXTENSIONS = setOf(".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".opus")
    const val MAX_AUDIO_SIZE_BYTES = 50L * 1024 * 1024 // 50 MB

    fun getFileFromUri(context: Context, uri: Uri): File? {
        return try {
            val inputStream: InputStream? = context.contentResolver.openInputStream(uri)
            val fileName = getFileName(context, uri)
            if (inputStream == null || fileName == null) return null

            val tempFile = File(context.cacheDir, fileName)
            val outputStream = FileOutputStream(tempFile)
            
            inputStream.use { input ->
                outputStream.use { output ->
                    input.copyTo(output)
                }
            }
            tempFile
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    fun validateImageFile(file: File): Result<Unit> {
        if (!file.exists() || !file.canRead()) {
            return Result.failure(Exception("File cannot be read or does not exist."))
        }
        val name = file.name.lowercase()
        val hasValidExt = ALLOWED_IMAGE_EXTENSIONS.any { name.endsWith(it) }
        if (!hasValidExt) {
            return Result.failure(Exception("Unsupported file type. Allowed formats: JPG, PNG, WEBP, BMP, TIFF."))
        }
        if (file.length() == 0L) {
            return Result.failure(Exception("Uploaded file is empty."))
        }
        if (file.length() > MAX_IMAGE_SIZE_BYTES) {
            val sizeMb = file.length().toDouble() / (1024 * 1024)
            return Result.failure(Exception("File size ${"%.1f".format(sizeMb)} MB exceeds the 20 MB limit for image uploads."))
        }
        return Result.success(Unit)
    }

    fun validateVideoFile(file: File): Result<Unit> {
        if (!file.exists() || !file.canRead()) {
            return Result.failure(Exception("File cannot be read or does not exist."))
        }
        val name = file.name.lowercase()
        val hasValidExt = ALLOWED_VIDEO_EXTENSIONS.any { name.endsWith(it) }
        if (!hasValidExt) {
            return Result.failure(Exception("Unsupported file type. Allowed video formats: MP4, MOV, AVI, MKV, WEBM, FLV, WMV."))
        }
        if (file.length() == 0L) {
            return Result.failure(Exception("Uploaded file is empty."))
        }
        if (file.length() > MAX_VIDEO_SIZE_BYTES) {
            val sizeMb = file.length().toDouble() / (1024 * 1024)
            return Result.failure(Exception("File size ${"%.1f".format(sizeMb)} MB exceeds the 500 MB limit for video uploads."))
        }
        return Result.success(Unit)
    }

    fun validateAudioFile(file: File): Result<Unit> {
        if (!file.exists() || !file.canRead()) {
            return Result.failure(Exception("File cannot be read or does not exist."))
        }
        val name = file.name.lowercase()
        val hasValidExt = ALLOWED_AUDIO_EXTENSIONS.any { name.endsWith(it) }
        if (!hasValidExt) {
            return Result.failure(Exception("Unsupported file type. Allowed audio formats: MP3, WAV, FLAC, AAC, OGG, M4A, OPUS."))
        }
        if (file.length() == 0L) {
            return Result.failure(Exception("Uploaded file is empty."))
        }
        if (file.length() > MAX_AUDIO_SIZE_BYTES) {
            val sizeMb = file.length().toDouble() / (1024 * 1024)
            return Result.failure(Exception("File size ${"%.1f".format(sizeMb)} MB exceeds the 50 MB limit for audio uploads."))
        }
        return Result.success(Unit)
    }

    fun loadVideoThumbnail(context: Context, uri: Uri): Bitmap? {
        return try {
            val retriever = android.media.MediaMetadataRetriever()
            retriever.setDataSource(context, uri)
            val bitmap = retriever.getFrameAtTime(0, android.media.MediaMetadataRetriever.OPTION_CLOSEST_SYNC)
            retriever.release()
            bitmap
        } catch (e: Exception) {
            null
        }
    }

    fun formatFileSize(bytes: Long): String {
        return when {
            bytes >= 1024 * 1024 -> "${"%.2f".format(bytes.toDouble() / (1024 * 1024))} MB"
            bytes >= 1024 -> "${"%.1f".format(bytes.toDouble() / 1024)} KB"
            else -> "$bytes B"
        }
    }

    fun loadBitmap(context: Context, uri: Uri): Bitmap? {
        return try {
            context.contentResolver.openInputStream(uri)?.use { stream ->
                BitmapFactory.decodeStream(stream)
            }
        } catch (e: Exception) {
            null
        }
    }

    fun decodeBitmap(bytes: ByteArray): Bitmap? {
        return try {
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
        } catch (e: Exception) {
            null
        }
    }

    private fun getFileName(context: Context, uri: Uri): String? {
        var result: String? = null
        if (uri.scheme == "content") {
            val cursor = context.contentResolver.query(uri, null, null, null, null)
            try {
                if (cursor != null && cursor.moveToFirst()) {
                    val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    if (index != -1) {
                        result = cursor.getString(index)
                    }
                }
            } finally {
                cursor?.close()
            }
        }
        if (result == null) {
            result = uri.path
            val cut = result?.lastIndexOf('/') ?: -1
            if (cut != -1) {
                result = result?.substring(cut + 1)
            }
        }
        return result
    }
}
