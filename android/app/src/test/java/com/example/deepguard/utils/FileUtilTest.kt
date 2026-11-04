package com.example.deepguard.utils

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class FileUtilTest {

    @Test
    fun testFormatFileSize() {
        assertEquals("500 B", FileUtil.formatFileSize(500L))
        assertEquals("1.5 KB", FileUtil.formatFileSize(1536L))
        assertEquals("2.00 MB", FileUtil.formatFileSize(2 * 1024 * 1024L))
    }

    @Test
    fun testValidateValidImageFile() {
        val tempFile = File.createTempFile("valid_test", ".jpg")
        try {
            tempFile.writeText("valid header data")
            val res = FileUtil.validateImageFile(tempFile)
            assertTrue(res.isSuccess)
        } finally {
            tempFile.delete()
        }
    }

    @Test
    fun testValidateEmptyImageFile() {
        val tempFile = File.createTempFile("empty_test", ".png")
        try {
            val res = FileUtil.validateImageFile(tempFile)
            assertTrue(res.isFailure)
            assertTrue(res.exceptionOrNull()?.message?.contains("empty") == true)
        } finally {
            tempFile.delete()
        }
    }

    @Test
    fun testValidateUnsupportedExtension() {
        val tempFile = File.createTempFile("unsupported_test", ".exe")
        try {
            tempFile.writeText("binary data")
            val res = FileUtil.validateImageFile(tempFile)
            assertTrue(res.isFailure)
            assertTrue(res.exceptionOrNull()?.message?.contains("Unsupported file type") == true)
        } finally {
            tempFile.delete()
        }
    }

    @Test
    fun testValidateNonExistentFile() {
        val missingFile = File("non_existent_file_12345.jpg")
        val res = FileUtil.validateImageFile(missingFile)
        assertTrue(res.isFailure)
        assertTrue(res.exceptionOrNull()?.message?.contains("does not exist") == true)
    }

    @Test
    fun testValidateValidVideoFile() {
        val tempFile = File.createTempFile("valid_video", ".mp4")
        try {
            tempFile.writeText("fake mp4 data")
            val res = FileUtil.validateVideoFile(tempFile)
            assertTrue(res.isSuccess)
        } finally {
            tempFile.delete()
        }
    }

    @Test
    fun testValidateEmptyVideoFile() {
        val tempFile = File.createTempFile("empty_video", ".mp4")
        try {
            val res = FileUtil.validateVideoFile(tempFile)
            assertTrue(res.isFailure)
            assertTrue(res.exceptionOrNull()?.message?.contains("empty") == true)
        } finally {
            tempFile.delete()
        }
    }

    @Test
    fun testValidateUnsupportedVideoExtension() {
        val tempFile = File.createTempFile("unsupported_video", ".pdf")
        try {
            tempFile.writeText("pdf data")
            val res = FileUtil.validateVideoFile(tempFile)
            assertTrue(res.isFailure)
            assertTrue(res.exceptionOrNull()?.message?.contains("Unsupported file type") == true)
        } finally {
            tempFile.delete()
        }
    }

    @Test
    fun testValidateValidAudioFile() {
        val tempFile = File.createTempFile("valid_audio", ".mp3")
        try {
            tempFile.writeText("fake mp3 data")
            val res = FileUtil.validateAudioFile(tempFile)
            assertTrue(res.isSuccess)
        } finally {
            tempFile.delete()
        }
    }

    @Test
    fun testValidateEmptyAudioFile() {
        val tempFile = File.createTempFile("empty_audio", ".wav")
        try {
            val res = FileUtil.validateAudioFile(tempFile)
            assertTrue(res.isFailure)
            assertTrue(res.exceptionOrNull()?.message?.contains("empty") == true)
        } finally {
            tempFile.delete()
        }
    }

    @Test
    fun testValidateUnsupportedAudioExtension() {
        val tempFile = File.createTempFile("unsupported_audio", ".zip")
        try {
            tempFile.writeText("zip data")
            val res = FileUtil.validateAudioFile(tempFile)
            assertTrue(res.isFailure)
            assertTrue(res.exceptionOrNull()?.message?.contains("Unsupported file type") == true)
        } finally {
            tempFile.delete()
        }
    }
}
