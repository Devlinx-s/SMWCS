import React, { useState, useEffect } from 'react'
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, ActivityIndicator, Alert,
  KeyboardAvoidingView, ScrollView
} from 'react-native'
import axios from 'axios'
import { AUTH_URL, COLORS } from '../config'
import { useAuthStore } from '../store/useStore'
import { initWS } from '../services/websocket'

const TRUCK_MAP = {
  'j.mwangi@smwcs.co.ke':  { id: 'b43d062c-a426-40f6-9404-3e19f9563a8a', label: 'KBZ 001A' },
  'p.kamau@smwcs.co.ke':   { id: '52e7898e-44aa-4b2e-b84d-4946567b728c', label: 'KBZ 002B' },
  'g.wanjiku@smwcs.co.ke': { id: '45e9a984-f8d1-4cc1-a60e-329c7ff2fd1b', label: 'KBZ 003C' },
}

export default function LoginScreen({ navigation }) {
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [loading,  setLoading]  = useState(false)
  const [showPass, setShowPass] = useState(false)
  const { setAuth, loadAuth }   = useAuthStore()

  useEffect(() => {
    loadAuth().then(({ token, truckId }) => {
      if (token && truckId) {
        initWS(truckId)
        navigation.replace('Main')
      }
    })
  }, [])

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert('Error', 'Please enter your email and password')
      return
    }
    setLoading(true)
    try {
      const res = await axios.post(
        `${AUTH_URL}/api/v1/auth/login`,
        { email: email.trim().toLowerCase(), password },
        { timeout: 10000 }
      )
      const token  = res.data.access_token
      const user   = res.data.user
      const truck  = TRUCK_MAP[email.trim().toLowerCase()]
      const truckId = truck?.id || null

      if (!truckId) {
        Alert.alert('Access Denied',
          'This account is not assigned to a truck.\nContact your dispatcher.')
        setLoading(false)
        return
      }

      await setAuth(token, user, truckId)
      initWS(truckId)
      navigation.replace('Main')
    } catch (err) {
      Alert.alert('Login Failed',
        err.response?.data?.detail || err.message || 'Check your credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <KeyboardAvoidingView style={styles.container} behavior="padding">
      <ScrollView contentContainerStyle={styles.scroll}
                  keyboardShouldPersistTaps="handled">
        <View style={styles.card}>
          <View style={styles.logoWrap}>
            <Text style={styles.logo}>🗑️</Text>
          </View>
          <Text style={styles.title}>SMWCS Driver</Text>
          <Text style={styles.subtitle}>Sign in to your account</Text>

          <View style={styles.inputWrap}>
            <Text style={styles.inputIcon}>✉️</Text>
            <TextInput
              style={styles.input}
              placeholder="Email address"
              placeholderTextColor={COLORS.gray}
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
              returnKeyType="next"
            />
          </View>

          <View style={styles.inputWrap}>
            <Text style={styles.inputIcon}>🔒</Text>
            <TextInput
              style={styles.input}
              placeholder="Password"
              placeholderTextColor={COLORS.gray}
              value={password}
              onChangeText={setPassword}
              secureTextEntry={!showPass}
              returnKeyType="done"
              onSubmitEditing={handleLogin}
            />
            <TouchableOpacity onPress={() => setShowPass(!showPass)}
                              style={styles.eyeBtn}>
              <Text style={styles.eyeIcon}>{showPass ? '🙈' : '👁️'}</Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity
            style={[styles.btn, loading && styles.btnDisabled]}
            onPress={handleLogin}
            disabled={loading}
          >
            {loading
              ? <ActivityIndicator color="#000" />
              : <Text style={styles.btnText}>Sign In</Text>
            }
          </TouchableOpacity>
        </View>

        <Text style={styles.footer}>
          SMWCS Kenya  ·  Nairobi Waste Collection System
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  container:  { flex: 1, backgroundColor: COLORS.bg },
  scroll:     { flexGrow: 1, justifyContent: 'center',
                alignItems: 'center', padding: 24 },
  card:       { width: '100%', maxWidth: 400,
                backgroundColor: COLORS.surface,
                borderRadius: 20, padding: 32, alignItems: 'center' },
  logoWrap:   { width: 80, height: 80, borderRadius: 40,
                backgroundColor: COLORS.teal,
                justifyContent: 'center', alignItems: 'center',
                marginBottom: 16 },
  logo:       { fontSize: 38 },
  title:      { fontSize: 22, fontWeight: 'bold',
                color: COLORS.white, marginBottom: 4 },
  subtitle:   { fontSize: 13, color: COLORS.gray, marginBottom: 28 },
  inputWrap:  { flexDirection: 'row', alignItems: 'center',
                backgroundColor: COLORS.surface2,
                borderRadius: 12, marginBottom: 14,
                paddingHorizontal: 12, width: '100%' },
  inputIcon:  { fontSize: 16, marginRight: 10 },
  input:      { flex: 1, padding: 14, color: COLORS.white, fontSize: 14 },
  eyeBtn:     { padding: 6 },
  eyeIcon:    { fontSize: 16 },
  btn:        { width: '100%', backgroundColor: COLORS.teal,
                borderRadius: 12, padding: 16,
                alignItems: 'center', marginTop: 8 },
  btnDisabled:{ opacity: 0.6 },
  btnText:    { color: '#000', fontWeight: 'bold', fontSize: 16 },
  footer:     { fontSize: 11, color: COLORS.gray,
                marginTop: 24, textAlign: 'center' },
})
