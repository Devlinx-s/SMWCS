import React, { useEffect } from 'react'
import {
  View, Text, ScrollView, TouchableOpacity,
  StyleSheet, Alert, Vibration
} from 'react-native'
import { useRouteStore, useAuthStore } from '../store/useStore'
import { sendMessage } from '../services/websocket'
import { COLORS } from '../config'

function StopCard({ stop, isCurrent, onComplete }) {
  return (
    <View style={[
      styles.stopCard,
      isCurrent && styles.stopCardActive,
      stop.completed && styles.stopCardDone
    ]}>
      <View style={styles.stopHeader}>
        <View style={[styles.orderBadge,
          isCurrent
            ? { backgroundColor: COLORS.teal }
            : stop.completed
              ? { backgroundColor: COLORS.green }
              : { backgroundColor: COLORS.surface2 }
        ]}>
          <Text style={styles.orderText}>
            {stop.completed ? '✓' : stop.stop_order}
          </Text>
        </View>
        <View style={{ flex: 1, marginLeft: 12 }}>
          <Text style={styles.stopSensor}>{stop.sensor_id || stop.bin_id}</Text>
          {stop.fill_pct != null && (
            <Text style={[styles.stopFill, {
              color: stop.fill_pct >= 90 ? COLORS.red
                   : stop.fill_pct >= 70 ? COLORS.amber
                   : COLORS.green
            }]}>
              Fill: {stop.fill_pct.toFixed(1)}%
            </Text>
          )}
          {stop.lat ? (
            <Text style={styles.stopCoords}>
              {stop.lat.toFixed(4)}, {stop.lon.toFixed(4)}
            </Text>
          ) : null}
        </View>
        {isCurrent && !stop.completed && (
          <TouchableOpacity style={styles.collectBtn} onPress={onComplete}>
            <Text style={styles.collectBtnText}>COLLECT</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  )
}

export default function HomeScreen() {
  const route          = useRouteStore(s => s.route)
  const wsConnected    = useRouteStore(s => s.wsConnected)
  const getCurrentStop = useRouteStore(s => s.getCurrentStop)
  const markStopDone   = useRouteStore(s => s.markStopDone)
  const truckId        = useAuthStore(s => s.truckId)
  const pendingAlert   = useRouteStore(s => s.pendingAlert)

  useEffect(() => {
    if (pendingAlert) {
      Vibration.vibrate([500, 200, 500, 200, 500])
      Alert.alert(
        'DISPATCH ALERT',
        pendingAlert.message || 'Alert from command center',
        [{ text: 'Acknowledge', onPress: () =>
          useRouteStore.setState({ pendingAlert: null }) }],
        { cancelable: false }
      )
    }
  }, [pendingAlert])

  const handleCollect = (stop) => {
    Alert.alert(
      'Confirm Collection',
      'Mark this bin as collected?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Confirm',
          onPress: () => {
            sendMessage({ type: 'STOP_COMPLETED', stop_id: stop.stop_id })
            markStopDone(stop.stop_id)
          }
        },
      ]
    )
  }

  const handleEmergency = () => {
    Alert.alert(
      'EMERGENCY',
      'Send emergency alert to command center?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'SEND ALERT',
          style: 'destructive',
          onPress: () => {
            Vibration.vibrate(1000)
            sendMessage({ type: 'DRIVER_EMERGENCY', lat: -1.2692, lon: 36.8090 })
            Alert.alert('Alert Sent', 'Command center has been notified')
          }
        },
      ]
    )
  }

  const currentStop = getCurrentStop()
  const stops       = route ? route.stops || [] : []
  const done        = stops.filter(s => s.completed).length
  const total       = stops.length
  const pct         = total > 0 ? Math.round(done / total * 100) : 0

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>Route Dashboard</Text>
          <Text style={styles.headerSub}>
            Truck: {truckId ? truckId.slice(0, 8) + '...' : '-'}
          </Text>
        </View>
        <View style={styles.headerRight}>
          <View style={[styles.wsDot,
            { backgroundColor: wsConnected ? COLORS.green : COLORS.red }]} />
          <Text style={styles.wsLabel}>
            {wsConnected ? 'Live' : 'Offline'}
          </Text>
        </View>
      </View>

      {route && (
        <View style={styles.progressSection}>
          <View style={styles.progressHeader}>
            <Text style={styles.progressLabel}>{done}/{total} stops completed</Text>
            <Text style={styles.progressPct}>{pct}%</Text>
          </View>
          <View style={styles.progressBar}>
            <View style={[styles.progressFill, { width: pct + '%' }]} />
          </View>
          <Text style={styles.zoneLabel}>
            Zone: {route.zone_id ? route.zone_id.slice(0, 8) + '...' : '-'}
          </Text>
        </View>
      )}

      <ScrollView style={styles.list} contentContainerStyle={{ paddingBottom: 20 }}>
        {!route && (
          <View style={styles.empty}>
            <Text style={styles.emptyIcon}>🗺️</Text>
            <Text style={styles.emptyText}>No active route assigned</Text>
            <Text style={styles.emptySubText}>
              {wsConnected ? 'Waiting for dispatch...' : 'Connecting to server...'}
            </Text>
          </View>
        )}
        {stops.map((stop, i) => (
          <StopCard
            key={stop.stop_id || i}
            stop={stop}
            isCurrent={currentStop && currentStop.stop_id === stop.stop_id}
            onComplete={() => handleCollect(stop)}
          />
        ))}
      </ScrollView>

      <TouchableOpacity style={styles.emergencyBtn} onPress={handleEmergency}>
        <Text style={styles.emergencyText}>EMERGENCY</Text>
      </TouchableOpacity>
    </View>
  )
}

const styles = StyleSheet.create({
  container:       { flex: 1, backgroundColor: COLORS.bg },
  header:          { flexDirection: 'row', justifyContent: 'space-between',
                     alignItems: 'center', backgroundColor: COLORS.surface,
                     padding: 16, paddingTop: 48 },
  headerTitle:     { fontSize: 18, fontWeight: 'bold', color: COLORS.white },
  headerSub:       { fontSize: 12, color: COLORS.gray, marginTop: 2 },
  headerRight:     { flexDirection: 'row', alignItems: 'center', gap: 6 },
  wsDot:           { width: 8, height: 8, borderRadius: 4 },
  wsLabel:         { fontSize: 12, color: COLORS.gray },
  progressSection: { backgroundColor: COLORS.surface, padding: 16,
                     borderBottomWidth: 1, borderBottomColor: COLORS.surface2 },
  progressHeader:  { flexDirection: 'row', justifyContent: 'space-between',
                     marginBottom: 6 },
  progressLabel:   { fontSize: 13, color: COLORS.gray },
  progressPct:     { fontSize: 13, fontWeight: 'bold', color: COLORS.teal },
  progressBar:     { height: 6, backgroundColor: COLORS.surface2,
                     borderRadius: 3, overflow: 'hidden' },
  progressFill:    { height: '100%', backgroundColor: COLORS.teal, borderRadius: 3 },
  zoneLabel:       { fontSize: 11, color: COLORS.gray, marginTop: 6 },
  list:            { flex: 1, padding: 12 },
  stopCard:        { backgroundColor: COLORS.surface, borderRadius: 12,
                     padding: 14, marginBottom: 10,
                     borderWidth: 1, borderColor: COLORS.surface2 },
  stopCardActive:  { borderColor: COLORS.teal, borderWidth: 2 },
  stopCardDone:    { opacity: 0.5 },
  stopHeader:      { flexDirection: 'row', alignItems: 'center' },
  orderBadge:      { width: 36, height: 36, borderRadius: 18,
                     justifyContent: 'center', alignItems: 'center' },
  orderText:       { color: COLORS.white, fontWeight: 'bold', fontSize: 14 },
  stopSensor:      { fontSize: 14, fontWeight: '600', color: COLORS.white },
  stopFill:        { fontSize: 13, marginTop: 2 },
  stopCoords:      { fontSize: 11, color: COLORS.gray, marginTop: 2 },
  collectBtn:      { backgroundColor: COLORS.teal, paddingHorizontal: 14,
                     paddingVertical: 8, borderRadius: 8 },
  collectBtnText:  { color: '#000', fontWeight: 'bold', fontSize: 13 },
  empty:           { alignItems: 'center', paddingTop: 80 },
  emptyIcon:       { fontSize: 48, marginBottom: 12 },
  emptyText:       { fontSize: 18, fontWeight: 'bold', color: COLORS.white, marginBottom: 6 },
  emptySubText:    { fontSize: 14, color: COLORS.gray, textAlign: 'center' },
  emergencyBtn:    { backgroundColor: COLORS.red, margin: 12,
                     borderRadius: 12, padding: 16, alignItems: 'center' },
  emergencyText:   { color: COLORS.white, fontWeight: 'bold', fontSize: 16, letterSpacing: 1 },
})
