import React from 'react'
import {
  View, Text, TouchableOpacity, StyleSheet,
  Alert, ScrollView
} from 'react-native'
import { useAuthStore, useRouteStore } from '../store/useStore'
import { disconnectWS, sendMessage } from '../services/websocket'
import { COLORS } from '../config'

const TRUCK_LABELS = {
  'b43d062c-a426-40f6-9404-3e19f9563a8a': 'KBZ 001A',
  '52e7898e-44aa-4b2e-b84d-4946567b728c': 'KBZ 002B',
  '45e9a984-f8d1-4cc1-a60e-329c7ff2fd1b': 'KBZ 003C',
}

function StatRow({ label, value, valueColor }) {
  return (
    <View style={styles.statRow}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={[styles.statValue, valueColor && { color: valueColor }]}>
        {value}
      </Text>
    </View>
  )
}

export default function StatusScreen({ navigation }) {
  const { truckId, driver, logout } = useAuthStore()
  const { route, wsConnected, offlineQueue } = useRouteStore()
  const stops = route?.stops || []
  const done  = stops.filter(s => s.completed).length

  const handleLogout = () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign Out',
        style: 'destructive',
        onPress: async () => {
          disconnectWS()
          await logout()
          navigation.getParent()?.replace('Login')
        }
      },
    ])
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Status</Text>
      </View>

      {/* Driver summary */}
      <TouchableOpacity
        style={styles.driverCard}
        onPress={() => navigation.navigate('Profile')}
        activeOpacity={0.8}
      >
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {driver ? driver.first_name?.[0] + driver.last_name?.[0] : '?'}
          </Text>
        </View>
        <View style={styles.driverInfo}>
          <Text style={styles.driverName}>
            {driver ? `${driver.first_name} ${driver.last_name}` : '—'}
          </Text>
          <Text style={styles.driverTruck}>
            {TRUCK_LABELS[truckId] || '—'}  ·  {driver?.role?.replace('_', ' ') || '—'}
          </Text>
        </View>
        <Text style={styles.chevron}>›</Text>
      </TouchableOpacity>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Connection</Text>
        <StatRow
          label="Server"
          value={wsConnected ? '● Connected' : '○ Disconnected'}
          valueColor={wsConnected ? COLORS.green : COLORS.red}
        />
        <StatRow
          label="Offline queue"
          value={`${offlineQueue.length} messages`}
          valueColor={offlineQueue.length > 0 ? COLORS.amber : COLORS.green}
        />
      </View>

      {route && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Current Route</Text>
          <StatRow label="Total stops"  value={String(stops.length)} />
          <StatRow label="Completed"    value={String(done)}
            valueColor={done === stops.length ? COLORS.green : COLORS.teal} />
          <StatRow label="Remaining"    value={String(stops.length - done)} />
        </View>
      )}

      <TouchableOpacity
        style={styles.profileBtn}
        onPress={() => navigation.navigate('Profile')}
      >
        <Text style={styles.profileBtnText}>👤  View Profile & Change Password</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.pingBtn}
        onPress={() => {
          sendMessage({ type: 'ping' })
          Alert.alert('Ping Sent', 'Check server logs for response')
        }}
      >
        <Text style={styles.pingText}>📡  Ping Server</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
        <Text style={styles.logoutText}>Sign Out</Text>
      </TouchableOpacity>

      <View style={{ height: 40 }} />
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container:   { flex: 1, backgroundColor: COLORS.bg },
  header:      { backgroundColor: COLORS.surface, padding: 16, paddingTop: 52 },
  title:       { fontSize: 18, fontWeight: 'bold', color: COLORS.white },
  driverCard:  { flexDirection: 'row', alignItems: 'center',
                 backgroundColor: COLORS.surface, margin: 12,
                 borderRadius: 14, padding: 16,
                 borderWidth: 1, borderColor: COLORS.teal },
  avatar:      { width: 48, height: 48, borderRadius: 24,
                 backgroundColor: COLORS.teal,
                 justifyContent: 'center', alignItems: 'center',
                 marginRight: 14 },
  avatarText:  { fontSize: 18, fontWeight: 'bold', color: '#fff' },
  driverInfo:  { flex: 1 },
  driverName:  { fontSize: 16, fontWeight: 'bold', color: COLORS.white },
  driverTruck: { fontSize: 12, color: COLORS.gray, marginTop: 2,
                 textTransform: 'capitalize' },
  chevron:     { fontSize: 22, color: COLORS.gray },
  card:        { backgroundColor: COLORS.surface, margin: 12,
                 marginBottom: 0, borderRadius: 12, padding: 16 },
  cardTitle:   { fontSize: 11, fontWeight: '700', color: COLORS.teal,
                 marginBottom: 12, textTransform: 'uppercase', letterSpacing: 0.8 },
  statRow:     { flexDirection: 'row', justifyContent: 'space-between',
                 alignItems: 'center', paddingVertical: 9,
                 borderBottomWidth: 1, borderBottomColor: COLORS.surface2 },
  statLabel:   { fontSize: 13, color: COLORS.gray },
  statValue:   { fontSize: 13, fontWeight: '600', color: COLORS.white },
  profileBtn:  { margin: 12, marginTop: 20, backgroundColor: COLORS.surface,
                 borderRadius: 12, padding: 14, alignItems: 'center',
                 borderWidth: 1, borderColor: COLORS.gray_dark },
  profileBtnText:{ color: COLORS.white, fontSize: 14 },
  pingBtn:     { margin: 12, marginTop: 8, backgroundColor: COLORS.surface,
                 borderRadius: 12, padding: 14, alignItems: 'center',
                 borderWidth: 1, borderColor: COLORS.teal },
  pingText:    { color: COLORS.teal, fontWeight: 'bold', fontSize: 14 },
  logoutBtn:   { margin: 12, marginTop: 8, backgroundColor: COLORS.surface,
                 borderRadius: 12, padding: 14, alignItems: 'center',
                 borderWidth: 1, borderColor: COLORS.red },
  logoutText:  { color: COLORS.red, fontWeight: 'bold', fontSize: 14 },
})
