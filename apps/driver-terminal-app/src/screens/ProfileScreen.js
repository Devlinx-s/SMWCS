import React, { useState } from 'react'
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, Alert, ScrollView, ActivityIndicator
} from 'react-native'
import axios from 'axios'
import { AUTH_URL, COLORS } from '../config'
import { useAuthStore } from '../store/useStore'

const TRUCK_LABELS = {
  'b43d062c-a426-40f6-9404-3e19f9563a8a': 'KBZ 001A',
  '52e7898e-44aa-4b2e-b84d-4946567b728c': 'KBZ 002B',
  '45e9a984-f8d1-4cc1-a60e-329c7ff2fd1b': 'KBZ 003C',
}

export default function ProfileScreen({ navigation }) {
  const { driver, token, truckId } = useAuthStore()
  const [oldPass,  setOldPass]  = useState('')
  const [newPass,  setNewPass]  = useState('')
  const [confirm,  setConfirm]  = useState('')
  const [loading,  setLoading]  = useState(false)
  const [showOld,  setShowOld]  = useState(false)
  const [showNew,  setShowNew]  = useState(false)

  const handleChangePassword = async () => {
    if (!oldPass || !newPass || !confirm) {
      Alert.alert('Error', 'Please fill in all fields')
      return
    }
    if (newPass !== confirm) {
      Alert.alert('Error', 'New passwords do not match')
      return
    }
    if (newPass.length < 8) {
      Alert.alert('Error', 'Password must be at least 8 characters')
      return
    }
    setLoading(true)
    try {
      await axios.post(
        `${AUTH_URL}/api/v1/auth/change-password`,
        { current_password: oldPass, new_password: newPass },
        { headers: { Authorization: `Bearer ${token}` }, timeout: 10000 }
      )
      Alert.alert('Success', 'Password changed successfully', [
        { text: 'OK', onPress: () => {
          setOldPass(''); setNewPass(''); setConfirm('')
        }}
      ])
    } catch (err) {
      Alert.alert('Failed',
        err.response?.data?.detail || 'Could not change password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}
                          style={styles.backBtn}>
          <Text style={styles.backText}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.title}>My Profile</Text>
      </View>

      {/* Profile card */}
      <View style={styles.profileCard}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {driver ? driver.first_name?.[0] + driver.last_name?.[0] : '?'}
          </Text>
        </View>
        <Text style={styles.name}>
          {driver ? `${driver.first_name} ${driver.last_name}` : '—'}
        </Text>
        <Text style={styles.role}>{driver?.role?.replace('_', ' ') || '—'}</Text>
      </View>

      {/* Info */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Account Details</Text>
        <View style={styles.row}>
          <Text style={styles.rowLabel}>Email</Text>
          <Text style={styles.rowValue}>{driver?.email || '—'}</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.rowLabel}>Assigned Truck</Text>
          <Text style={[styles.rowValue, { color: COLORS.teal }]}>
            {TRUCK_LABELS[truckId] || '—'}
          </Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.rowLabel}>Account Status</Text>
          <Text style={[styles.rowValue, { color: COLORS.green }]}>Active</Text>
        </View>
      </View>

      {/* Change password */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Change Password</Text>

        <Text style={styles.label}>Current Password</Text>
        <View style={styles.inputWrap}>
          <TextInput
            style={styles.input}
            placeholder="Enter current password"
            placeholderTextColor={COLORS.gray}
            value={oldPass}
            onChangeText={setOldPass}
            secureTextEntry={!showOld}
          />
          <TouchableOpacity onPress={() => setShowOld(!showOld)}>
            <Text style={styles.eye}>{showOld ? '🙈' : '👁️'}</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.label}>New Password</Text>
        <View style={styles.inputWrap}>
          <TextInput
            style={styles.input}
            placeholder="Enter new password"
            placeholderTextColor={COLORS.gray}
            value={newPass}
            onChangeText={setNewPass}
            secureTextEntry={!showNew}
          />
          <TouchableOpacity onPress={() => setShowNew(!showNew)}>
            <Text style={styles.eye}>{showNew ? '🙈' : '👁️'}</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.label}>Confirm New Password</Text>
        <View style={styles.inputWrap}>
          <TextInput
            style={styles.input}
            placeholder="Confirm new password"
            placeholderTextColor={COLORS.gray}
            value={confirm}
            onChangeText={setConfirm}
            secureTextEntry
          />
        </View>

        <TouchableOpacity
          style={[styles.btn, loading && styles.btnDisabled]}
          onPress={handleChangePassword}
          disabled={loading}
        >
          {loading
            ? <ActivityIndicator color="#000" />
            : <Text style={styles.btnText}>Update Password</Text>
          }
        </TouchableOpacity>
      </View>

      <View style={{ height: 40 }} />
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container:   { flex: 1, backgroundColor: COLORS.bg },
  header:      { backgroundColor: COLORS.surface, padding: 16,
                 paddingTop: 52, flexDirection: 'row', alignItems: 'center' },
  backBtn:     { marginRight: 16 },
  backText:    { color: COLORS.teal, fontSize: 14, fontWeight: '600' },
  title:       { fontSize: 18, fontWeight: 'bold', color: COLORS.white },
  profileCard: { backgroundColor: COLORS.surface, margin: 12,
                 borderRadius: 16, padding: 24, alignItems: 'center' },
  avatar:      { width: 70, height: 70, borderRadius: 35,
                 backgroundColor: COLORS.teal,
                 justifyContent: 'center', alignItems: 'center',
                 marginBottom: 12 },
  avatarText:  { fontSize: 26, fontWeight: 'bold', color: '#fff' },
  name:        { fontSize: 20, fontWeight: 'bold',
                 color: COLORS.white, marginBottom: 4 },
  role:        { fontSize: 13, color: COLORS.gray,
                 textTransform: 'capitalize' },
  card:        { backgroundColor: COLORS.surface, margin: 12,
                 marginBottom: 0, borderRadius: 12, padding: 16 },
  cardTitle:   { fontSize: 11, fontWeight: '700', color: COLORS.teal,
                 marginBottom: 14, textTransform: 'uppercase',
                 letterSpacing: 0.8 },
  row:         { flexDirection: 'row', justifyContent: 'space-between',
                 alignItems: 'center', paddingVertical: 10,
                 borderBottomWidth: 1, borderBottomColor: COLORS.surface2 },
  rowLabel:    { fontSize: 13, color: COLORS.gray },
  rowValue:    { fontSize: 13, fontWeight: '600', color: COLORS.white },
  label:       { fontSize: 11, color: COLORS.gray, marginBottom: 6,
                 marginTop: 12, fontWeight: '700',
                 textTransform: 'uppercase', letterSpacing: 0.5 },
  inputWrap:   { flexDirection: 'row', alignItems: 'center',
                 backgroundColor: COLORS.surface2,
                 borderRadius: 10, paddingHorizontal: 12 },
  input:       { flex: 1, padding: 12, color: COLORS.white, fontSize: 14 },
  eye:         { fontSize: 16, padding: 6 },
  btn:         { backgroundColor: COLORS.teal, borderRadius: 10,
                 padding: 14, alignItems: 'center', marginTop: 20 },
  btnDisabled: { opacity: 0.6 },
  btnText:     { color: '#000', fontWeight: 'bold', fontSize: 15 },
})
