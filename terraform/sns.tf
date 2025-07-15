# a topic for general bird alerts, can later make one per species
resource "aws_sns_topic" "bird_alerts" {
  name = "bird-detection-alerts"
}
